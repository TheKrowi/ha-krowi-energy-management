"""TTF DAM gas price store for Krowi Energy Management."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from homeassistant.core import HomeAssistant, callback  # type: ignore
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore
from homeassistant.helpers.dispatcher import async_dispatcher_send  # type: ignore
from homeassistant.helpers.event import async_track_time_change  # type: ignore

from .const import SIGNAL_TTF_DAM_UPDATE

_LOGGER = logging.getLogger(__name__)

_API_URL = "https://mijn.elindus.be/marketinfo/dayahead/prices"


class TtfDamStore:
    """Fetches and caches daily TTF DAM gas prices from the Elindus API.

    Fetch schedule:
    - Startup: immediate fetch
    - Midnight (00:00:01): set data_is_fresh=False, re-fetch
    - Every 30-min tick (X:00:01, X:30:01): if not data_is_fresh, fetch

    Prices are converted from EUR/MWh to c€/kWh at ingest (divide by 10).
    """

    def __init__(self) -> None:
        self._hass: HomeAssistant | None = None
        self._today_price: float | None = None
        self._average: float | None = None
        self._data_is_fresh: bool = False
        self._unsubs: list = []

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def async_start(self, hass: HomeAssistant) -> None:
        """Start the store: subscribe to time events and run initial fetch."""
        self._hass = hass

        # Midnight: reset freshness and re-fetch
        self._unsubs.append(
            async_track_time_change(hass, self._on_midnight, hour=0, minute=0, second=1)
        )
        # Every 30-min tick: retry if not fresh
        self._unsubs.append(
            async_track_time_change(hass, self._on_tick, minute=[0, 30], second=1)
        )

        # Initial fetch
        await self.async_fetch()

    async def async_stop(self) -> None:
        """Stop the store: unsubscribe all time-change listeners."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    # -------------------------------------------------------------------------
    # Fetch
    # -------------------------------------------------------------------------

    async def async_fetch(self) -> None:
        """Fetch latest TTF DAM prices from the Elindus API."""
        today = date.today()
        from_date = (today - timedelta(days=30)).isoformat()
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
            async_dispatcher_send(self._hass, SIGNAL_TTF_DAM_UPDATE)
            return

        try:
            average_raw = data["statistics"]["averagePrice"]
            entries = sorted(data["dataSeries"]["data"], key=lambda e: e["x"])
            last = entries[-1]
            today_raw = last["y"]
            # Parse Unix ms timestamp to date
            last_date = datetime.utcfromtimestamp(last["x"] / 1000).date()
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            _LOGGER.error("TtfDamStore: failed to parse response: %s", exc)
            async_dispatcher_send(self._hass, SIGNAL_TTF_DAM_UPDATE)
            return

        # Convert EUR/MWh → c€/kWh (divide by 10)
        self._average = average_raw / 10
        self._today_price = today_raw / 10
        self._data_is_fresh = last_date == today

        _LOGGER.debug(
            "TtfDamStore: average=%.5f c€/kWh, today=%.5f c€/kWh, fresh=%s",
            self._average,
            self._today_price,
            self._data_is_fresh,
        )

        async_dispatcher_send(self._hass, SIGNAL_TTF_DAM_UPDATE)

    # -------------------------------------------------------------------------
    # Time-change callbacks
    # -------------------------------------------------------------------------

    @callback
    def _on_midnight(self, now: datetime) -> None:
        """Handle midnight tick: reset freshness flag and re-fetch."""
        self._data_is_fresh = False
        self._hass.async_create_task(self.async_fetch())

    @callback
    def _on_tick(self, now: datetime) -> None:
        """Handle 30-min tick: retry fetch if data is not yet fresh."""
        if not self._data_is_fresh:
            self._hass.async_create_task(self.async_fetch())

    # -------------------------------------------------------------------------
    # Public properties
    # -------------------------------------------------------------------------

    @property
    def today_price(self) -> float | None:
        """Latest daily TTF DAM price in c€/kWh; None until first successful fetch."""
        return self._today_price

    @property
    def average(self) -> float | None:
        """30-day average TTF DAM price in c€/kWh; None until first successful fetch."""
        return self._average

    @property
    def data_is_fresh(self) -> bool:
        """True if the latest fetched data point is dated today."""
        return self._data_is_fresh
