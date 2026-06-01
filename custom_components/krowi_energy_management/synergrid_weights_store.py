"""Abstract base class for Synergrid annual weights stores (RLP and SPP)."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import date, datetime

from homeassistant.core import HomeAssistant, callback  # type: ignore
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore
from homeassistant.helpers.event import async_track_time_change  # type: ignore
from homeassistant.helpers.storage import Store  # type: ignore

_LOGGER = logging.getLogger(__name__)
_STORAGE_VERSION = 1


class _SynergridWeightsStore(ABC):
    """Base class for stores that download, cache, and serve Synergrid annual weight profiles.

    Subclasses implement the file-format-specific parse function and storage
    envelope logic. All lifecycle management (midnight reload, year-boundary
    rollover, December pre-fetch, HA Storage persistence) is provided here.
    """

    def __init__(self) -> None:
        self._hass: HomeAssistant | None = None
        self._weights: dict[str, list[float]] = {}  # ISO date → weight list
        self._storage: Store | None = None
        self._available: bool = False
        self._loaded_year: int = 0
        self._next_year_prefetch_done: bool = False
        self._unsubs: list = []

    @property
    def available(self) -> bool:
        """True if weights were successfully loaded for the current year."""
        return self._available

    # -------------------------------------------------------------------------
    # Abstract interface — subclasses must implement all of these
    # -------------------------------------------------------------------------

    @property
    @abstractmethod
    def _label(self) -> str:
        """Short label used in log messages and notification IDs, e.g. 'RLP' or 'SPP'."""

    @abstractmethod
    def _url_for_year(self, year: int) -> str:
        """Return the download URL for the given year."""

    @abstractmethod
    def _storage_key_for_year(self, year: int) -> str:
        """Return the HA Storage key for the given year."""

    @abstractmethod
    def _parse_file(self, data: bytes, year: int) -> dict[str, list[float]]:
        """Parse raw file bytes and return ISO-date → weight-list mapping.

        This method is called via async_add_executor_job and must be synchronous.
        """

    @abstractmethod
    def _build_envelope(self, year: int, weights: dict[str, list[float]]) -> dict:
        """Build the dict to persist to HA Storage."""

    @abstractmethod
    def _cache_valid(self, raw: dict, year: int) -> bool:
        """Return True if the cached storage envelope is valid for the current config."""

    # -------------------------------------------------------------------------
    # Optional hooks — override in subclasses for extra state updates
    # -------------------------------------------------------------------------

    def _profile_description(self) -> str:
        """Human-readable profile label used in notification messages."""
        return self._label

    def _on_weights_downloaded(self, weights: dict[str, list[float]]) -> None:
        """Called after a successful download+parse. Override for extra state updates."""

    def _on_loaded_from_cache(self) -> None:
        """Called after a successful cache load. Override for extra state updates."""

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def _async_start(self, hass: HomeAssistant) -> None:
        """Shared startup body. Call from the subclass async_start after subclass-specific init."""
        self._hass = hass
        year = date.today().year
        self._loaded_year = year
        self._storage = Store(hass, _STORAGE_VERSION, self._storage_key_for_year(year))

        # Register midnight listener unconditionally — even the warm-cache path needs it
        # to detect year rollover and trigger December pre-fetching.
        self._unsubs.append(
            async_track_time_change(hass, self._on_midnight, hour=0, minute=0, second=1)
        )

        loaded = await self._async_load(year)
        today_iso = date.today().isoformat()

        if loaded and today_iso in self._weights:
            self._available = True
            self._on_loaded_from_cache()
            _LOGGER.debug(
                "Synergrid%sStore: loaded %d days from storage for year %d",
                self._label,
                len(self._weights),
                year,
            )
            from homeassistant.components import persistent_notification  # noqa: PLC0415

            persistent_notification.async_dismiss(
                self._hass, f"krowi_{self._label.lower()}_load_failed"
            )
            persistent_notification.async_dismiss(
                self._hass, f"krowi_{self._label.lower()}_today_missing"
            )
            return

        _LOGGER.debug(
            "Synergrid%sStore: today (%s) not in cache — downloading for year %d",
            self._label,
            today_iso,
            year,
        )
        await self._async_download_and_parse(year, context="startup")

        if self._available and today_iso not in self._weights:
            from homeassistant.components import persistent_notification  # noqa: PLC0415

            desc = self._profile_description()
            persistent_notification.async_create(
                self._hass,
                (
                    f"{desc} profile for {year} was loaded but does not contain today "
                    f"({today_iso}).\n\n"
                    f"Today's {desc}-weighted average will use the unweighted fallback."
                ),
                title=f"Krowi: {self._label} profile missing today \u2139\ufe0f",
                notification_id=f"krowi_{self._label.lower()}_today_missing",
            )

    async def async_stop(self) -> None:
        """Stop the store: unsubscribe time listeners."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    # -------------------------------------------------------------------------
    # Year-boundary reload
    # -------------------------------------------------------------------------

    @callback
    def _on_midnight(self, now: datetime) -> None:
        """At midnight: reload if the year changed; pre-fetch next year from Dec 26."""
        if now.year != self._loaded_year:
            self._next_year_prefetch_done = False
            self._hass.async_create_task(self._async_reload_for_year(now.year))
        elif now.month == 12 and now.day >= 26 and not self._next_year_prefetch_done:
            self._hass.async_create_task(self._async_prefetch_next_year(now.year + 1))

    async def _async_reload_for_year(self, year: int) -> None:
        """Swap storage key and reload (from cache or download) for the new year."""
        _LOGGER.info(
            "Synergrid%sStore: year changed to %d — reloading profile", self._label, year
        )
        self._storage = Store(self._hass, _STORAGE_VERSION, self._storage_key_for_year(year))
        loaded = await self._async_load(year)
        today_iso = date.today().isoformat()

        if loaded and today_iso in self._weights:
            self._available = True
            self._loaded_year = year
            self._on_loaded_from_cache()
            _LOGGER.info(
                "Synergrid%sStore: loaded %d days from storage for year %d",
                self._label,
                len(self._weights),
                year,
            )
            from homeassistant.components import persistent_notification  # noqa: PLC0415

            persistent_notification.async_dismiss(
                self._hass, f"krowi_{self._label.lower()}_load_failed"
            )
            persistent_notification.async_dismiss(
                self._hass, f"krowi_{self._label.lower()}_today_missing"
            )
            return

        await self._async_download_and_parse(year, context="year rollover")
        if self._available:
            self._loaded_year = year
            if today_iso not in self._weights:
                from homeassistant.components import persistent_notification  # noqa: PLC0415

                desc = self._profile_description()
                persistent_notification.async_create(
                    self._hass,
                    (
                        f"{desc} profile for {year} loaded after year rollover but does not "
                        f"contain today ({today_iso}).\n\n"
                        f"Today's {desc}-weighted average will use the unweighted fallback."
                    ),
                    title=f"Krowi: {self._label} profile missing today \u2139\ufe0f",
                    notification_id=f"krowi_{self._label.lower()}_today_missing",
                )

    async def _async_prefetch_next_year(self, year: int) -> None:
        """Try to pre-fetch and cache next year's profile (Dec 26–31).

        Sends a persistent HA notification on success (once per session) or
        on every failure.
        """
        from homeassistant.components import persistent_notification  # noqa: PLC0415

        label = self._label
        desc = self._profile_description()
        _pref_success_id = f"krowi_{label.lower()}_prefetch_success"
        _pref_failed_id = f"krowi_{label.lower()}_prefetch_failed"

        _LOGGER.debug("Synergrid%sStore: attempting pre-fetch for year %d", label, year)

        # Check if already cached for next year
        next_storage = Store(
            self._hass, _STORAGE_VERSION, self._storage_key_for_year(year)
        )
        try:
            raw = await next_storage.async_load()
        except Exception:  # noqa: BLE001
            raw = None

        if (
            raw
            and isinstance(raw, dict)
            and self._cache_valid(raw, year)
            and isinstance(raw.get("weights"), dict)
            and raw["weights"]
        ):
            _LOGGER.info("Synergrid%sStore: year %d profile already cached", label, year)
            self._next_year_prefetch_done = True
            persistent_notification.async_dismiss(self._hass, _pref_failed_id)
            persistent_notification.async_create(
                self._hass,
                f"Year {year} {desc} profile is ready in cache.",
                title=f"Krowi: {label} profile pre-fetched \u2705",
                notification_id=_pref_success_id,
            )
            return

        # Download
        url = self._url_for_year(year)
        session = async_get_clientsession(self._hass)
        try:
            async with session.get(url) as resp:
                resp.raise_for_status()
                data = await resp.read()
            weights = await self._hass.async_add_executor_job(self._parse_file, data, year)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning(
                "Synergrid%sStore: pre-fetch for year %d failed: %s", label, year, exc
            )
            persistent_notification.async_create(
                self._hass,
                (
                    f"Failed to pre-fetch year {year} {desc} profile: {exc}\n\n"
                    "Will retry at midnight. The profile may not be published yet."
                ),
                title=f"Krowi: {label} pre-fetch failed \u26a0\ufe0f",
                notification_id=_pref_failed_id,
            )
            return

        if not weights:
            _LOGGER.warning(
                "Synergrid%sStore: pre-fetch for year %d returned 0 days — not yet published",
                label,
                year,
            )
            persistent_notification.async_create(
                self._hass,
                (
                    f"Year {year} {desc} profile downloaded but contained 0 days. "
                    "The file may not be published yet — will retry at midnight."
                ),
                title=f"Krowi: {label} pre-fetch incomplete \u26a0\ufe0f",
                notification_id=_pref_failed_id,
            )
            return

        # Persist to next year's storage key
        try:
            await next_storage.async_save(self._build_envelope(year, weights))
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning(
                "Synergrid%sStore: failed to persist year %d pre-fetch: %s", label, year, exc
            )

        self._next_year_prefetch_done = True
        persistent_notification.async_dismiss(self._hass, _pref_failed_id)
        persistent_notification.async_create(
            self._hass,
            f"Year {year} {desc} profile successfully pre-fetched and cached ({len(weights)} days).",
            title=f"Krowi: {label} profile pre-fetched \u2705",
            notification_id=_pref_success_id,
        )
        _LOGGER.info(
            "Synergrid%sStore: pre-fetched and cached year %d profile (%d days)",
            label,
            year,
            len(weights),
        )

    # -------------------------------------------------------------------------
    # Load / Download / Persist
    # -------------------------------------------------------------------------

    async def _async_load(self, year: int) -> bool:
        """Load weights from HA Storage. Returns True if data was loaded successfully."""
        try:
            raw = await self._storage.async_load()
        except Exception as exc:
            _LOGGER.warning(
                "Synergrid%sStore: failed to load from storage: %s", self._label, exc
            )
            return False

        if not isinstance(raw, dict):
            return False

        if not self._cache_valid(raw, year):
            _LOGGER.debug(
                "Synergrid%sStore: cached data does not match current configuration — discarding",
                self._label,
            )
            return False

        raw_weights = raw.get("weights")
        if not isinstance(raw_weights, dict):
            return False

        weights: dict[str, list[float]] = {}
        for key, val in raw_weights.items():
            if isinstance(val, list) and val:
                try:
                    weights[key] = [float(w) for w in val]
                except (ValueError, TypeError):
                    pass

        if not weights:
            return False

        self._weights = weights
        return True

    async def _async_download_and_parse(self, year: int, context: str = "startup") -> None:
        """Download and parse the profile file for the given year."""
        from homeassistant.components import persistent_notification  # noqa: PLC0415

        label = self._label
        desc = self._profile_description()
        notif_id = f"krowi_{label.lower()}_load_failed"
        _degraded = "unavailable" if context == "startup" else "falling back to unweighted means"
        _restart = " Restart HA to retry." if context == "startup" else ""

        url = self._url_for_year(year)
        session = async_get_clientsession(self._hass)
        try:
            async with session.get(url) as resp:
                resp.raise_for_status()
                data = await resp.read()
        except Exception as exc:
            _LOGGER.warning(
                "Synergrid%sStore: failed to download %s profile for year %d: %s",
                label,
                label,
                year,
                exc,
            )
            self._available = False
            persistent_notification.async_create(
                self._hass,
                (
                    f"{desc} profile for {year} could not be downloaded ({context}): {exc}\n\n"
                    f"{label}-weighted sensors are {_degraded}.{_restart}"
                ),
                title=f"Krowi: {label} profile unavailable \u26a0\ufe0f",
                notification_id=notif_id,
            )
            return

        try:
            weights = await self._hass.async_add_executor_job(self._parse_file, data, year)
        except Exception as exc:
            _LOGGER.warning(
                "Synergrid%sStore: failed to parse %s profile for year %d: %s",
                label,
                label,
                year,
                exc,
            )
            self._available = False
            persistent_notification.async_create(
                self._hass,
                (
                    f"{desc} profile for {year} downloaded but failed to parse ({context}): {exc}\n\n"
                    f"The file format may have changed. {label}-weighted sensors are {_degraded}.{_restart}"
                ),
                title=f"Krowi: {label} profile parse error \u26a0\ufe0f",
                notification_id=notif_id,
            )
            return

        if not weights:
            _LOGGER.warning(
                "Synergrid%sStore: parsed 0 days for year %d — unexpected format",
                label,
                year,
            )
            self._available = False
            persistent_notification.async_create(
                self._hass,
                (
                    f"{desc} profile for {year} downloaded but contained 0 days ({context}).\n\n"
                    f"The file format may have changed. {label}-weighted sensors are {_degraded}.{_restart}"
                ),
                title=f"Krowi: {label} profile empty \u26a0\ufe0f",
                notification_id=notif_id,
            )
            return

        self._weights = weights
        self._available = True
        self._on_weights_downloaded(weights)
        _LOGGER.debug(
            "Synergrid%sStore: downloaded and parsed %d days for year %d",
            label,
            len(weights),
            year,
        )
        persistent_notification.async_dismiss(self._hass, notif_id)
        await self._async_persist(year)

    async def _async_persist(self, year: int) -> None:
        """Save weights to HA Storage."""
        try:
            await self._storage.async_save(self._build_envelope(year, self._weights))
        except Exception as exc:
            _LOGGER.warning(
                "Synergrid%sStore: failed to save to storage: %s", self._label, exc
            )

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def has_date(self, d: date) -> bool:
        """Return True iff weights are cached for date d."""
        return d.isoformat() in self._weights

    def get_weights(self, d: date) -> list[float] | None:
        """Return the weight list for date d, or None if unavailable."""
        return self._weights.get(d.isoformat())

    def action_store_state(self) -> dict:
        """Return a snapshot of the current in-memory store state."""
        sorted_dates = sorted(self._weights.keys())
        return {
            "available": self._available,
            "loaded_year": self._loaded_year,
            "date_count": len(self._weights),
            "has_today": date.today().isoformat() in self._weights,
            "first_date": sorted_dates[0] if sorted_dates else None,
            "last_date": sorted_dates[-1] if sorted_dates else None,
        }

    async def async_action_test_fetch(self, year: int) -> dict:
        """Live download + parse for the given year. Does NOT modify store state."""
        url = self._url_for_year(year)
        session = async_get_clientsession(self._hass)
        http_status: int | None = None

        try:
            async with session.get(url) as resp:
                http_status = resp.status
                resp.raise_for_status()
                data = await resp.read()
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "year": year,
                "http_status": http_status,
                "date_count": None,
                "has_today": None,
                "first_date": None,
                "last_date": None,
                "error": str(exc),
            }

        try:
            weights = await self._hass.async_add_executor_job(self._parse_file, data, year)
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "year": year,
                "http_status": http_status,
                "date_count": None,
                "has_today": None,
                "first_date": None,
                "last_date": None,
                "error": str(exc),
            }

        sorted_dates = sorted(weights.keys())
        today_iso = date.today().isoformat()
        return {
            "ok": len(weights) > 0,
            "year": year,
            "http_status": http_status,
            "date_count": len(weights),
            "has_today": today_iso in weights,
            "first_date": sorted_dates[0] if sorted_dates else None,
            "last_date": sorted_dates[-1] if sorted_dates else None,
            "error": None if weights else f"Parsed 0 days for year {year}",
        }
