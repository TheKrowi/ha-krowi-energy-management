"""Nord Pool BE day-ahead price store for Krowi Energy Management."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from statistics import mean
from typing import TYPE_CHECKING

from dateutil.relativedelta import relativedelta # type: ignore

from homeassistant.core import HomeAssistant, callback # type: ignore
from homeassistant.helpers.aiohttp_client import async_get_clientsession # type: ignore
from homeassistant.helpers.dispatcher import async_dispatcher_send # type: ignore
from homeassistant.helpers.event import async_call_later, async_track_time_change # type: ignore
from homeassistant.helpers.storage import Store # type: ignore
from homeassistant.util import dt as dt_utils # type: ignore

from .const import SIGNAL_NORDPOOL_UPDATE

if TYPE_CHECKING:
    from .rlp_store import SynergridRLPStore
    from .spp_store import SynergridSPPStore

_LOGGER = logging.getLogger(__name__)

_API_URL = "https://dataportal-api.nordpoolgroup.com/api/DayAheadPrices"


_STORAGE_KEY = "krowi_energy_management_nordpool_daily_avg"
_STORAGE_VERSION = 1


class NordpoolBeStore:
    """Fetches, caches and serves Nord Pool BE 15-minute day-ahead price data.

    Fetch schedule:
    - Startup: load buffer from storage, fetch today, gap-fill missing days, fetch tomorrow if >= 13:00
    - Midnight (00:00:01): snapshot yesterday's average, re-fetch today, clear tomorrow cache
    - 13:01:00: fetch tomorrow if not yet valid
    - Every 15-min tick (X:00:01, X:15:01, X:30:01, X:45:01):
        update current_price from cache, retry tomorrow if needed, dispatch signal

    Daily average buffer:
    - _daily_avg_buffer: dict[date, float] — completed days in rolling calendar-month window
    - Persisted via HA Storage; today is always live from _data_today, never stored
    """

    def __init__(self) -> None:
        self._hass: HomeAssistant | None = None
        self._low_price_cutoff: float = 1.0
        self._data_today: list[dict] = []
        self._data_tomorrow: list[dict] = []
        self._tomorrow_valid: bool = False
        self._current_price: float | None = None
        self._daily_avg_buffer: dict[date, float] = {}
        self._daily_rlp_buffer: dict[date, float] = {}
        self._daily_spp_buffer: dict[date, float] = {}
        self._storage: Store | None = None
        self._rlp_storage: Store | None = None
        self._spp_storage: Store | None = None
        self._rlp_store: SynergridRLPStore | None = None
        self._spp_store: SynergridSPPStore | None = None
        self._unsubs: list = []
        self._backfill_retry_unsub: object | None = None

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def async_start(self, hass: HomeAssistant, low_price_cutoff: float, rlp_store: SynergridRLPStore | None = None, spp_store: SynergridSPPStore | None = None) -> None:
        """Start the store: subscribe to time events and run initial fetches."""
        self._hass = hass
        self._low_price_cutoff = low_price_cutoff
        self._rlp_store = rlp_store
        self._spp_store = spp_store
        self._storage = Store(hass, _STORAGE_VERSION, _STORAGE_KEY)
        self._rlp_storage = Store(hass, _STORAGE_VERSION, "krowi_energy_management_nordpool_daily_rlp_avg")
        self._spp_storage = Store(hass, _STORAGE_VERSION, "krowi_energy_management_nordpool_daily_spp_avg")

        # Midnight: snapshot yesterday, refresh today, clear tomorrow
        self._unsubs.append(
            async_track_time_change(hass, self._on_midnight, hour=0, minute=0, second=1)
        )
        # 13:01: try to fetch tomorrow
        self._unsubs.append(
            async_track_time_change(hass, self._on_thirteen, hour=13, minute=1, second=0)
        )
        # Every 15-min tick at :01 past each quarter
        self._unsubs.append(
            async_track_time_change(hass, self._on_tick, minute=[0, 15, 30, 45], second=1)
        )

        # Load persisted buffers
        await self._async_load_buffer()
        await self._async_load_rlp_buffer()
        await self._async_load_spp_buffer()

        # Trim stale entries from storage immediately (trim normally runs at midnight,
        # so after a restart old entries outside the calendar-month window would persist
        # until the next midnight tick and inflate the weighted averages).
        self._trim_buffer()

        # Initial fetches
        await self.async_fetch_today()
        if dt_utils.now().hour >= 13:
            await self.async_fetch_tomorrow()

        self._update_current_price()

        # Backfill any missing days in the calendar-month window
        await self._async_backfill()

        async_dispatcher_send(hass, SIGNAL_NORDPOOL_UPDATE)

    async def async_stop(self) -> None:
        """Stop the store: unsubscribe all time-change listeners."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        if self._backfill_retry_unsub is not None:
            self._backfill_retry_unsub()
            self._backfill_retry_unsub = None

    # -------------------------------------------------------------------------
    # Fetch methods
    # -------------------------------------------------------------------------

    async def async_fetch_today(self) -> None:
        """Fetch today's 15-min price slots from the Nord Pool API."""
        date_str = dt_utils.now().strftime("%Y-%m-%d")
        slots = await self._async_fetch(date_str)
        if slots is not None:
            self._data_today = slots
            _LOGGER.debug(
                "NordpoolBeStore: fetched %d slots for today (%s)", len(slots), date_str
            )

    async def async_fetch_tomorrow(self) -> None:
        """Fetch tomorrow's 15-min price slots from the Nord Pool API."""
        date_str = (dt_utils.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        slots = await self._async_fetch(date_str)
        if slots:
            self._data_tomorrow = slots
            self._tomorrow_valid = True
            _LOGGER.debug(
                "NordpoolBeStore: fetched %d slots for tomorrow (%s)", len(slots), date_str
            )
        else:
            _LOGGER.debug(
                "NordpoolBeStore: no slots yet for tomorrow (%s)", date_str
            )

    async def _async_fetch(self, date_str: str) -> list[dict] | None:
        """Fetch and parse price slots for a given date. Returns None on error."""
        session = async_get_clientsession(self._hass)
        url = f"{_API_URL}?currency=EUR&market=DayAhead&deliveryArea=BE&date={date_str}"
        try:
            async with session.get(url) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except Exception as exc:
            _LOGGER.error(
                "NordpoolBeStore: failed to fetch prices for %s: %s", date_str, exc
            )
            async_dispatcher_send(self._hass, SIGNAL_NORDPOOL_UPDATE)
            return None

        try:
            slots = [
                {
                    "start": datetime.fromisoformat(entry["deliveryStart"]),
                    "end": datetime.fromisoformat(entry["deliveryEnd"]),
                    "value": round(entry["entryPerArea"]["BE"] / 10, 5),
                }
                for entry in data["multiAreaEntries"]
            ]
        except (KeyError, ValueError, TypeError) as exc:
            _LOGGER.error(
                "NordpoolBeStore: failed to parse response for %s: %s", date_str, exc
            )
            async_dispatcher_send(self._hass, SIGNAL_NORDPOOL_UPDATE)
            return None

        return slots

    # -------------------------------------------------------------------------
    # Buffer helpers (tasks 1.3–1.5, 3.1)
    # -------------------------------------------------------------------------

    async def _async_load_buffer(self) -> None:
        """Load the daily average buffer from HA Storage."""
        try:
            raw = await self._storage.async_load()
        except Exception as exc:
            _LOGGER.warning("NordpoolBeStore: failed to load buffer from storage: %s", exc)
            raw = None

        if not isinstance(raw, dict):
            self._daily_avg_buffer = {}
            return

        buf: dict[date, float] = {}
        for key, val in raw.items():
            try:
                buf[date.fromisoformat(key)] = float(val)
            except (ValueError, TypeError):
                pass
        self._daily_avg_buffer = buf
        _LOGGER.debug("NordpoolBeStore: loaded %d buffer entries from storage", len(buf))

    async def _async_load_rlp_buffer(self) -> None:
        """Load the RLP daily buffer from HA Storage."""
        try:
            raw = await self._rlp_storage.async_load()
        except Exception as exc:
            _LOGGER.warning("NordpoolBeStore: failed to load RLP buffer from storage: %s", exc)
            raw = None

        if not isinstance(raw, dict):
            self._daily_rlp_buffer = {}
            return

        buf: dict[date, float] = {}
        for key, val in raw.items():
            try:
                buf[date.fromisoformat(key)] = float(val)
            except (ValueError, TypeError):
                pass
        self._daily_rlp_buffer = buf
        _LOGGER.debug("NordpoolBeStore: loaded %d RLP buffer entries from storage", len(buf))

    def _save_buffer(self) -> None:
        """Persist the daily average buffer to HA Storage (fire-and-forget)."""
        payload = {d.isoformat(): v for d, v in self._daily_avg_buffer.items()}
        self._hass.async_create_task(self._storage.async_save(payload))

    def _save_rlp_buffer(self) -> None:
        """Persist the RLP buffer to HA Storage (fire-and-forget)."""
        payload = {d.isoformat(): v for d, v in self._daily_rlp_buffer.items()}
        self._hass.async_create_task(self._rlp_storage.async_save(payload))

    async def _async_load_spp_buffer(self) -> None:
        """Load the SPP daily buffer from HA Storage."""
        try:
            raw = await self._spp_storage.async_load()
        except Exception as exc:
            _LOGGER.warning("NordpoolBeStore: failed to load SPP buffer from storage: %s", exc)
            raw = None

        if not isinstance(raw, dict):
            self._daily_spp_buffer = {}
            return

        buf: dict[date, float] = {}
        for key, val in raw.items():
            try:
                buf[date.fromisoformat(key)] = float(val)
            except (ValueError, TypeError):
                pass
        self._daily_spp_buffer = buf
        _LOGGER.debug("NordpoolBeStore: loaded %d SPP buffer entries from storage", len(buf))

    def _save_spp_buffer(self) -> None:
        """Persist the SPP buffer to HA Storage (fire-and-forget)."""
        payload = {d.isoformat(): v for d, v in self._daily_spp_buffer.items()}
        self._hass.async_create_task(self._spp_storage.async_save(payload))

    def _trim_buffer(self) -> None:
        """Remove entries older than one calendar month from all buffers."""
        cutoff = date.today() - relativedelta(months=1)
        to_remove = [d for d in self._daily_avg_buffer if d < cutoff]
        for d in to_remove:
            del self._daily_avg_buffer[d]
        to_remove_rlp = [d for d in self._daily_rlp_buffer if d < cutoff]
        for d in to_remove_rlp:
            del self._daily_rlp_buffer[d]
        to_remove_spp = [d for d in self._daily_spp_buffer if d < cutoff]
        for d in to_remove_spp:
            del self._daily_spp_buffer[d]

    def _snapshot_today(self) -> None:
        """Snapshot today's average into all buffers as yesterday's entry (called at midnight)."""
        avg = self.average
        if avg is None:
            return
        yesterday = date.today() - timedelta(days=1)
        # Unweighted buffer (unchanged)
        self._daily_avg_buffer[yesterday] = avg
        # RLP-weighted buffer
        rlp_avg = self._compute_rlp_avg(yesterday, self._data_today)
        self._daily_rlp_buffer[yesterday] = rlp_avg
        # SPP-weighted buffer
        spp_avg = self._compute_spp_avg(yesterday, self._data_today)
        self._daily_spp_buffer[yesterday] = spp_avg
        self._trim_buffer()
        self._save_buffer()
        self._save_rlp_buffer()
        self._save_spp_buffer()
        _LOGGER.debug(
            "NordpoolBeStore: snapshotted daily average %.5f for %s (rlp_avg=%.5f) (spp_avg=%.5f)",
            avg, yesterday, rlp_avg, spp_avg,
        )

    def _compute_rlp_avg(self, d: date, slots: list[dict]) -> float:
        """Return the RLP-weighted daily average for the given slots in c€/kWh.

        Falls back to the unweighted mean when RLP weights are unavailable.
        """
        if not slots:
            return 0.0
        weights = self._rlp_store.get_weights(d) if self._rlp_store else None
        if weights and len(weights) == len(slots):
            wt = sum(weights)
            if wt > 0:
                return sum(slot["value"] * w for slot, w in zip(slots, weights)) / wt
        return mean(slot["value"] for slot in slots)

    def _compute_spp_avg(self, d: date, slots: list[dict]) -> float:
        """Return the SPP-weighted daily average for the given slots in c€/kWh.

        Falls back to the unweighted mean when SPP weights are unavailable.
        """
        if not slots:
            return 0.0
        weights = self._spp_store.get_weights(d) if self._spp_store else None
        if weights and len(weights) == len(slots):
            wt = sum(weights)
            if wt > 0:
                return sum(slot["value"] * w for slot, w in zip(slots, weights)) / wt
        return mean(slot["value"] for slot in slots)

    # -------------------------------------------------------------------------
    # Backfill (task 2.1)
    # -------------------------------------------------------------------------

    async def _async_backfill(self) -> None:
        """Fetch any missing days in the calendar-month window and insert into buffer.

        Checks the avg, RLP, and SPP buffers independently so that a gap in
        any one of them triggers a (re-)fetch even when the other buffers are
        complete.  If any fetch fails (e.g. rate-limited), the missing dates
        are retried every 60 seconds until all gaps are filled.
        """
        # Cancel any pending retry before starting a new pass.
        if self._backfill_retry_unsub is not None:
            self._backfill_retry_unsub()
            self._backfill_retry_unsub = None

        today = date.today()
        cutoff = today - relativedelta(months=1)
        yesterday = today - timedelta(days=1)

        # Build the set of required dates: cutoff (inclusive) to yesterday (inclusive)
        required: set[date] = set()
        d = cutoff
        while d <= yesterday:
            required.add(d)
            d += timedelta(days=1)

        # Check each buffer independently — a complete avg buffer must not hide
        # gaps in the RLP/SPP buffers.
        all_to_fetch = sorted(
            (required - set(self._daily_avg_buffer.keys()))
            | (required - set(self._daily_rlp_buffer.keys()))
            | (required - set(self._daily_spp_buffer.keys()))
        )
        if not all_to_fetch:
            return

        _LOGGER.debug("NordpoolBeStore: backfilling %d day(s)", len(all_to_fetch))
        changed = False
        skipped: list[date] = []
        for missing_date in all_to_fetch:
            date_str = missing_date.isoformat()
            slots = await self._async_fetch(date_str)
            if not slots:
                skipped.append(missing_date)
                continue
            if missing_date not in self._daily_avg_buffer:
                daily_avg = round(mean(slot["value"] for slot in slots), 5)
                self._daily_avg_buffer[missing_date] = daily_avg
                _LOGGER.debug("NordpoolBeStore: backfilled avg %s = %.5f", date_str, daily_avg)
            if missing_date not in self._daily_rlp_buffer:
                self._daily_rlp_buffer[missing_date] = self._compute_rlp_avg(missing_date, slots)
            if missing_date not in self._daily_spp_buffer:
                self._daily_spp_buffer[missing_date] = self._compute_spp_avg(missing_date, slots)
            changed = True

        if changed:
            self._trim_buffer()
            self._save_buffer()
            self._save_rlp_buffer()
            self._save_spp_buffer()

        if skipped:
            _LOGGER.warning(
                "NordpoolBeStore: backfill could not fetch %d day(s) (%s … %s) — "
                "will retry in 60 s",
                len(skipped),
                skipped[0].isoformat(),
                skipped[-1].isoformat(),
            )
            self._backfill_retry_unsub = async_call_later(
                self._hass, 60, self._on_backfill_retry
            )

    @callback
    def _on_backfill_retry(self, _now: datetime) -> None:
        """Scheduled callback to retry backfill after a failed fetch."""
        self._backfill_retry_unsub = None
        self._hass.async_create_task(self._async_backfill())

    # -------------------------------------------------------------------------
    # Time-change callbacks
    # -------------------------------------------------------------------------

    @callback
    def _on_midnight(self, now: datetime) -> None:
        """Handle midnight tick: snapshot yesterday, reset tomorrow cache, re-fetch today."""
        self._snapshot_today()  # capture yesterday's average BEFORE clearing _data_today
        self._data_tomorrow = []
        self._tomorrow_valid = False
        self._hass.async_create_task(self._do_midnight_refresh())

    async def _do_midnight_refresh(self) -> None:
        await self.async_fetch_today()
        self._update_current_price()
        async_dispatcher_send(self._hass, SIGNAL_NORDPOOL_UPDATE)

    @callback
    def _on_thirteen(self, now: datetime) -> None:
        """Handle 13:01 tick: try to fetch tomorrow's prices."""
        if not self._tomorrow_valid:
            self._hass.async_create_task(self._do_tomorrow_fetch())

    async def _do_tomorrow_fetch(self) -> None:
        await self.async_fetch_tomorrow()
        async_dispatcher_send(self._hass, SIGNAL_NORDPOOL_UPDATE)

    @callback
    def _on_tick(self, now: datetime) -> None:
        """Handle 15-min tick: update current price from cache, dispatch signal."""
        self._update_current_price()
        # Retry tomorrow fetch on every tick from 13:00 until valid
        if not self._tomorrow_valid and dt_utils.now().hour >= 13:
            self._hass.async_create_task(self._do_tomorrow_fetch())
        async_dispatcher_send(self._hass, SIGNAL_NORDPOOL_UPDATE)

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _update_current_price(self) -> None:
        """Find the active slot in data_today and set current_price."""
        now = dt_utils.now()
        for slot in self._data_today:
            if slot["start"] <= now < slot["end"]:
                self._current_price = slot["value"]
                return
        self._current_price = None

    # -------------------------------------------------------------------------
    # Public properties
    # -------------------------------------------------------------------------

    @property
    def current_price(self) -> float | None:
        """Value of the currently active 15-min slot in c€/kWh."""
        return self._current_price

    @property
    def average(self) -> float | None:
        """Mean of all today's slot values in c€/kWh, rounded to 5dp."""
        if not self._data_today:
            return None
        return round(mean(slot["value"] for slot in self._data_today), 5)

    @property
    def monthly_average(self) -> float | None:
        """Rolling calendar-month average in c€/kWh (buffer + today-live), rounded to 5dp."""
        today_avg = self.average
        if today_avg is None:
            return None
        completed = list(self._daily_avg_buffer.values())
        if not completed:
            return round(today_avg, 5)
        return round(mean([*completed, today_avg]), 5)

    @property
    def monthly_average_rlp(self) -> float | None:
        """Rolling calendar-month RLP-weighted average in c€/kWh, rounded to 5dp."""
        if self.average is None:
            return None
        today_rlp = self._compute_rlp_avg(date.today(), self._data_today)
        all_avgs = list(self._daily_rlp_buffer.values()) + [today_rlp]
        return round(mean(all_avgs), 5)

    @property
    def monthly_average_spp(self) -> float | None:
        """Rolling calendar-month SPP-weighted average in c€/kWh, rounded to 5dp."""
        if self.average is None:
            return None
        today_spp = self._compute_spp_avg(date.today(), self._data_today)
        all_avgs = list(self._daily_spp_buffer.values()) + [today_spp]
        return round(mean(all_avgs), 5)

    def rlp_fully_available(self) -> bool:
        """Return True if all days in the rolling window had real RLP weights."""
        if self._rlp_store is None:
            return False
        cutoff = date.today() - relativedelta(months=1)
        yesterday = date.today() - timedelta(days=1)
        d = cutoff
        while d <= yesterday:
            if not self._rlp_store.has_date(d):
                return False
            d += timedelta(days=1)
        return self._rlp_store.has_date(date.today())

    @property
    def low_price(self) -> bool | None:
        """True if current_price < average * low_price_cutoff."""
        cp = self._current_price
        avg = self.average
        if cp is None or avg is None:
            return None
        return cp < avg * self._low_price_cutoff

    @property
    def price_percent_to_average(self) -> float | None:
        """current_price / average, rounded to 5dp."""
        cp = self._current_price
        avg = self.average
        if cp is None or avg is None or avg == 0:
            return None
        return round(cp / avg, 5)

    @property
    def today(self) -> list[float]:
        """All today's slot values in chronological order."""
        return [slot["value"] for slot in self._data_today]

    @property
    def tomorrow(self) -> list[float]:
        """All tomorrow's slot values in chronological order, or [] if not yet valid."""
        if not self._tomorrow_valid:
            return []
        return [slot["value"] for slot in self._data_tomorrow]

    @property
    def tomorrow_valid(self) -> bool:
        """True if tomorrow's price data has been successfully fetched."""
        return self._tomorrow_valid
