"""Nord Pool BE day-ahead price store for Krowi Energy Management."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from statistics import mean

from homeassistant.core import HomeAssistant, callback # type: ignore
from homeassistant.helpers.aiohttp_client import async_get_clientsession # type: ignore
from homeassistant.helpers.dispatcher import async_dispatcher_send # type: ignore
from homeassistant.helpers.event import async_track_time_change # type: ignore
from homeassistant.util import dt as dt_utils # type: ignore

from .const import SIGNAL_NORDPOOL_UPDATE

_LOGGER = logging.getLogger(__name__)

_API_URL = "https://dataportal-api.nordpoolgroup.com/api/DayAheadPrices"


class NordpoolBeStore:
    """Fetches, caches and serves Nord Pool BE 15-minute day-ahead price data.

    Fetch schedule:
    - Startup: fetch today; fetch tomorrow if now >= 13:00
    - Midnight (00:00:01): re-fetch today, clear tomorrow cache
    - 13:01:00: fetch tomorrow if not yet valid
    - Every 15-min tick (X:00:01, X:15:01, X:30:01, X:45:01):
        update current_price from cache, retry tomorrow if needed, dispatch signal
    """

    def __init__(self) -> None:
        self._hass: HomeAssistant | None = None
        self._low_price_cutoff: float = 1.0
        self._data_today: list[dict] = []
        self._data_tomorrow: list[dict] = []
        self._tomorrow_valid: bool = False
        self._current_price: float | None = None
        self._unsubs: list = []

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def async_start(self, hass: HomeAssistant, low_price_cutoff: float) -> None:
        """Start the store: subscribe to time events and run initial fetches."""
        self._hass = hass
        self._low_price_cutoff = low_price_cutoff

        # Midnight: refresh today, clear tomorrow
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

        # Initial fetches
        await self.async_fetch_today()
        if dt_utils.now().hour >= 13:
            await self.async_fetch_tomorrow()

        self._update_current_price()
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
    # Time-change callbacks
    # -------------------------------------------------------------------------

    @callback
    def _on_midnight(self, now: datetime) -> None:
        """Handle midnight tick: reset tomorrow cache, re-fetch today."""
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
