"""Nord Pool BE day-ahead price store for Krowi Energy Management."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from statistics import mean

from dateutil.relativedelta import relativedelta

from homeassistant.core import HomeAssistant, callback # type: ignore
from homeassistant.helpers.aiohttp_client import async_get_clientsession # type: ignore
from homeassistant.helpers.dispatcher import async_dispatcher_send # type: ignore
from homeassistant.helpers.event import async_track_time_change # type: ignore
from homeassistant.helpers.storage import Store # type: ignore
from homeassistant.util import dt as dt_utils # type: ignore

from .const import SIGNAL_NORDPOOL_UPDATE

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
        self._storage: Store | None = None
        self._unsubs: list = []

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def async_start(self, hass: HomeAssistant, low_price_cutoff: float) -> None:
        """Start the store: subscribe to time events and run initial fetches."""
        self._hass = hass
        self._low_price_cutoff = low_price_cutoff
        self._storage = Store(hass, _STORAGE_VERSION, _STORAGE_KEY)

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

        # Load persisted buffer
        await self._async_load_buffer()

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

    def _save_buffer(self) -> None:
        """Persist the daily average buffer to HA Storage (fire-and-forget)."""
        payload = {d.isoformat(): v for d, v in self._daily_avg_buffer.items()}
        self._hass.async_create_task(self._storage.async_save(payload))

    def _trim_buffer(self) -> None:
        """Remove entries older than one calendar month."""
        cutoff = date.today() - relativedelta(months=1)
        to_remove = [d for d in self._daily_avg_buffer if d < cutoff]
        for d in to_remove:
            del self._daily_avg_buffer[d]

    def _snapshot_today(self) -> None:
        """Snapshot today's average into the buffer as yesterday's entry (called at midnight)."""
        avg = self.average
        if avg is None:
            return
        yesterday = date.today() - timedelta(days=1)
        self._daily_avg_buffer[yesterday] = avg
        self._trim_buffer()
        self._save_buffer()
        _LOGGER.debug("NordpoolBeStore: snapshotted daily average %.5f for %s", avg, yesterday)

    # -------------------------------------------------------------------------
    # Backfill (task 2.1)
    # -------------------------------------------------------------------------

    async def _async_backfill(self) -> None:
        """Fetch any missing days in the calendar-month window and insert into buffer."""
        today = date.today()
        cutoff = today - relativedelta(months=1)
        yesterday = today - timedelta(days=1)

        # Build the set of required dates: cutoff (inclusive) to yesterday (inclusive)
        required: set[date] = set()
        d = cutoff
        while d <= yesterday:
            required.add(d)
            d += timedelta(days=1)

        missing = sorted(required - set(self._daily_avg_buffer.keys()))
        if not missing:
            return

        _LOGGER.debug("NordpoolBeStore: backfilling %d missing day(s)", len(missing))
        changed = False
        for missing_date in missing:
            date_str = missing_date.isoformat()
            slots = await self._async_fetch(date_str)
            if not slots:
                _LOGGER.debug("NordpoolBeStore: backfill skipped %s (no data)", date_str)
                continue
            daily_avg = round(mean(slot["value"] for slot in slots), 5)
            self._daily_avg_buffer[missing_date] = daily_avg
            changed = True
            _LOGGER.debug("NordpoolBeStore: backfilled %s = %.5f", date_str, daily_avg)

        if changed:
            self._trim_buffer()
            self._save_buffer()

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
