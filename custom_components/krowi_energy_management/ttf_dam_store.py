"""TTF DAM gas price store for Krowi Energy Management."""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from statistics import mean

from dateutil.relativedelta import relativedelta # type: ignore

from homeassistant.core import HomeAssistant, callback  # type: ignore
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore
from homeassistant.helpers.dispatcher import async_dispatcher_send  # type: ignore
from homeassistant.helpers.event import async_track_time_change  # type: ignore
from homeassistant.helpers.storage import Store  # type: ignore
from homeassistant.util import dt as dt_utils  # type: ignore

from .const import SIGNAL_TTF_DAM_UPDATE

_LOGGER = logging.getLogger(__name__)

_API_URL = "https://mijn.elindus.be/marketinfo/dayahead/prices"
_STORAGE_KEY = "krowi_energy_management_ttf_dam_daily"
_STORAGE_VERSION = 1


class TtfDamStore:
    """Fetches and caches daily TTF DAM gas prices from the Elindus API.

    Fetch schedule:
    - Startup: load buffer from storage, trim, save, then immediate fetch
    - Midnight (00:00:01): re-fetch (freshness derived from buffer)
    - Every 30-min tick (X:00:01, X:30:01): if not data_is_fresh, fetch

    Fetch window: one calendar month (today - relativedelta(months=1) to today).
    All returned entries are merged into the daily buffer. The buffer is persisted
    to HA Storage so sensors survive restarts.
    Prices are converted from EUR/MWh to c€/kWh at ingest (divide by 10).

    Race fix: _fetch_in_flight guard prevents concurrent fetches when midnight
    and 30-min ticks coincide at 00:00:01.

    Timezone fix: dt_utils.now().date() is used everywhere instead of date.today()
    to honour HA's configured timezone (avoids UTC vs local date mismatch on Docker).
    """

    def __init__(self) -> None:
        self._hass: HomeAssistant | None = None
        self._daily_buffer: dict[date, float] = {}
        self._fetch_in_flight: bool = False
        self._storage: Store | None = None
        self._unsubs: list = []

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def async_start(self, hass: HomeAssistant) -> None:
        """Start the store: load buffer, subscribe to time events and run initial fetch."""
        self._hass = hass
        self._storage = Store(hass, _STORAGE_VERSION, _STORAGE_KEY)

        # Midnight: re-fetch (buffer key for today absent → retry loop starts)
        self._unsubs.append(
            async_track_time_change(hass, self._on_midnight, hour=0, minute=0, second=1)
        )
        # Every 30-min tick: retry if not fresh
        self._unsubs.append(
            async_track_time_change(hass, self._on_tick, minute=[0, 30], second=1)
        )

        # Load persisted buffer, trim stale entries accumulated during restart gap
        await self._async_load_buffer()
        self._trim_buffer()
        self._save_buffer()

        # Initial fetch
        await self.async_fetch()

    async def async_stop(self) -> None:
        """Stop the store: unsubscribe all time-change listeners."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    # -------------------------------------------------------------------------
    # Buffer helpers
    # -------------------------------------------------------------------------

    async def _async_load_buffer(self) -> None:
        """Load the daily price buffer from HA Storage."""
        try:
            raw = await self._storage.async_load()
        except Exception as exc:
            _LOGGER.warning("TtfDamStore: failed to load buffer from storage: %s", exc)
            raw = None

        if not isinstance(raw, dict):
            self._daily_buffer = {}
            return

        buf: dict[date, float] = {}
        for key, val in raw.items():
            try:
                buf[date.fromisoformat(key)] = float(val)
            except (ValueError, TypeError):
                pass
        self._daily_buffer = buf
        _LOGGER.debug("TtfDamStore: loaded %d buffer entries from storage", len(buf))

    def _trim_buffer(self) -> None:
        """Remove entries older than one calendar month."""
        cutoff = dt_utils.now().date() - relativedelta(months=1)
        to_remove = [d for d in self._daily_buffer if d < cutoff]
        for d in to_remove:
            del self._daily_buffer[d]

    def _save_buffer(self) -> None:
        """Persist the daily buffer to HA Storage (fire-and-forget)."""
        payload = {d.isoformat(): v for d, v in self._daily_buffer.items()}
        self._hass.async_create_task(self._storage.async_save(payload))

    # -------------------------------------------------------------------------
    # Fetch
    # -------------------------------------------------------------------------

    async def async_fetch(self) -> None:
        """Fetch latest TTF DAM prices from the Elindus API."""
        if self._fetch_in_flight:
            return
        self._fetch_in_flight = True
        try:
            await self._do_fetch()
        finally:
            self._fetch_in_flight = False

    async def _do_fetch(self) -> None:
        """Internal: perform the actual HTTP fetch and merge into buffer."""
        today = dt_utils.now().date()
        from_date = (today - relativedelta(months=1)).isoformat()
        to_date = today.isoformat()

        session = async_get_clientsession(self._hass)
        url = (
            f"{_API_URL}?from={from_date}&to={to_date}&market=GAS&granularity=DAY"
        )
        try:
            async with session.get(url) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except Exception as exc:
            _LOGGER.error("TtfDamStore: failed to fetch prices: %s", exc)
            from homeassistant.components import persistent_notification  # noqa: PLC0415
            persistent_notification.async_create(
                self._hass,
                f"TTF DAM price data could not be fetched: {exc}\n\nGas spot price sensors may show stale data.",
                title="Krowi: TTF DAM fetch failed \u26a0\ufe0f",
                notification_id="krowi_ttf_dam_fetch_failed",
            )
            async_dispatcher_send(self._hass, SIGNAL_TTF_DAM_UPDATE)
            return

        try:
            entries = data["dataSeries"]["data"]
            if not isinstance(entries, list):
                raise TypeError(f"expected list, got {type(entries).__name__}")
        except (KeyError, TypeError) as exc:
            _LOGGER.error("TtfDamStore: failed to parse response: %s", exc)
            from homeassistant.components import persistent_notification  # noqa: PLC0415
            persistent_notification.async_create(
                self._hass,
                f"TTF DAM response could not be parsed: {exc}\n\nGas spot price sensors may show stale data.",
                title="Krowi: TTF DAM fetch failed \u26a0\ufe0f",
                notification_id="krowi_ttf_dam_fetch_failed",
            )
            async_dispatcher_send(self._hass, SIGNAL_TTF_DAM_UPDATE)
            return

        # Merge all returned entries into the buffer
        merged = 0
        for entry in entries:
            try:
                local_date = dt_utils.as_local(
                    datetime.fromtimestamp(entry["x"] / 1000, tz=timezone.utc)
                ).date()
                value = float(entry["y"]) / 10  # EUR/MWh → c€/kWh
                self._daily_buffer[local_date] = value
                merged += 1
            except (KeyError, ValueError, TypeError):
                pass

        self._trim_buffer()
        self._save_buffer()

        _LOGGER.debug(
            "TtfDamStore: merged %d entries; buffer=%d; today_price=%s c€/kWh; fresh=%s",
            merged,
            len(self._daily_buffer),
            self._daily_buffer.get(today),
            self.data_is_fresh,
        )
        from homeassistant.components import persistent_notification  # noqa: PLC0415
        persistent_notification.async_dismiss(self._hass, "krowi_ttf_dam_fetch_failed")
        async_dispatcher_send(self._hass, SIGNAL_TTF_DAM_UPDATE)

    # -------------------------------------------------------------------------
    # Time-change callbacks
    # -------------------------------------------------------------------------

    @callback
    def _on_midnight(self, now: datetime) -> None:
        """Handle midnight tick: re-fetch (today's key is absent → retry loop active)."""
        self._hass.async_create_task(self.async_fetch())

    @callback
    def _on_tick(self, now: datetime) -> None:
        """Handle 30-min tick: retry fetch if data is not yet fresh."""
        if not self.data_is_fresh:
            self._hass.async_create_task(self.async_fetch())

    # -------------------------------------------------------------------------
    # Public properties
    # -------------------------------------------------------------------------

    @property
    def today_price(self) -> float | None:
        """Latest daily TTF DAM price in c€/kWh; None if today's data not yet fetched."""
        return self._daily_buffer.get(dt_utils.now().date())

    @property
    def rolling_average(self) -> float | None:
        """Rolling ~30-day average TTF DAM price in c€/kWh; None if buffer is empty."""
        cutoff = dt_utils.now().date() - relativedelta(months=1)
        values = [v for d, v in self._daily_buffer.items() if d >= cutoff]
        return mean(values) if values else None

    @property
    def month_average(self) -> float | None:
        """Calendar-month-to-date average TTF DAM price in c€/kWh; None if no entries yet."""
        first_of_month = dt_utils.now().date().replace(day=1)
        values = [v for d, v in self._daily_buffer.items() if d >= first_of_month]
        return mean(values) if values else None

    @property
    def data_is_fresh(self) -> bool:
        """True if today's price is present in the buffer."""
        return dt_utils.now().date() in self._daily_buffer
