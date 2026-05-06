"""Synergrid RLP0N electricity profile store for Krowi Energy Management."""
from __future__ import annotations

import io
import logging
from datetime import date, datetime

from homeassistant.core import HomeAssistant, callback  # type: ignore
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore
from homeassistant.helpers.event import async_track_time_change  # type: ignore
from homeassistant.helpers.storage import Store  # type: ignore

_LOGGER = logging.getLogger(__name__)

_RLP_URL_PATTERN = (
    "https://www.synergrid.be/images/downloads/SLP-RLP-SPP/"
    "{year}/RLP0N%20{year}%20Electricity%20all%20DSOs.xlsb"
)
_STORAGE_KEY_PATTERN = "krowi_energy_management_rlp_{year}"
_STORAGE_VERSION = 1


def _parse_xlsb(data: bytes, year: int, dso_name: str) -> dict[str, list[float]]:
    """Parse the Synergrid RLP0N all-DSOs .xlsb file in a worker thread.

    Returns a dict mapping ISO date strings (YYYY-MM-DD) to a list of
    96 (±4 for DST) weight floats for the specified DSO.
    """
    import pyxlsb  # type: ignore  # noqa: PLC0415

    result: dict[str, list[float]] = {}
    with pyxlsb.open_workbook(io.BytesIO(data)) as wb:
        with wb.get_sheet("RLP96UbyDGO") as sheet:
            rows = list(sheet.rows())

    # Row 1 (index 1): DGO names starting at col 7
    if len(rows) < 4:
        _LOGGER.warning("SynergridRLPStore: unexpected file format — too few rows")
        return result

    dgo_header = rows[1]
    dso_col = None
    for col_idx, cell in enumerate(dgo_header):
        if cell and cell.v == dso_name:
            dso_col = col_idx
            break

    if dso_col is None:
        _LOGGER.warning(
            "SynergridRLPStore: DSO '%s' not found in RLP96UbyDGO header row",
            dso_name,
        )
        return result

    # Row 3+ (index 3+): data rows
    for row in rows[3:]:
        vals = [c.v if c else None for c in row]
        if len(vals) <= dso_col or vals[1] is None:
            continue
        key = f"{int(vals[1])}-{int(vals[2]):02d}-{int(vals[3]):02d}"
        w = vals[dso_col]
        if w is not None:
            try:
                result.setdefault(key, []).append(float(w))
            except (ValueError, TypeError):
                pass

    return result


class SynergridRLPStore:
    """Downloads, caches and serves the annual Synergrid RLP0N electricity weights."""

    def __init__(self) -> None:
        self._hass: HomeAssistant | None = None
        self._weights: dict[str, list[float]] = {}  # ISO date → weight list
        self._storage: Store | None = None
        self._available: bool = False
        self._rlp_available_dates: set[str] = set()  # dates with real RLP weights
        self._dso_name: str = ""
        self._loaded_year: int = 0
        self._next_year_prefetch_done: bool = False
        self._unsubs: list = []

    @property
    def available(self) -> bool:
        """True if weights were successfully loaded for the current year."""
        return self._available

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def async_start(self, hass: HomeAssistant, dso_name: str) -> None:
        """Start the store: load from HA Storage or download if needed."""
        self._hass = hass
        year = date.today().year
        self._loaded_year = year
        key = _STORAGE_KEY_PATTERN.format(year=year)
        self._storage = Store(hass, _STORAGE_VERSION, key)

        # Attempt to load from storage
        loaded = await self._async_load(year, dso_name)
        today_iso = date.today().isoformat()

        if loaded and today_iso in self._weights:
            self._available = True
            self._dso_name = dso_name
            self._rlp_available_dates = set(self._weights.keys())
            _LOGGER.debug(
                "SynergridRLPStore: loaded %d days from storage for year %d",
                len(self._weights),
                year,
            )
            from homeassistant.components import persistent_notification  # noqa: PLC0415
            persistent_notification.async_dismiss(self._hass, "krowi_rlp_load_failed")
            persistent_notification.async_dismiss(self._hass, "krowi_rlp_today_missing")
            return

        # Need to download
        _LOGGER.debug(
            "SynergridRLPStore: today (%s) not in cache — downloading for year %d",
            today_iso,
            year,
        )
        await self._async_download_and_parse(year, dso_name, context="startup")

        if self._available and today_iso not in self._weights:
            from homeassistant.components import persistent_notification  # noqa: PLC0415
            persistent_notification.async_create(
                self._hass,
                (
                    f"RLP profile for {year} was loaded but does not contain today "
                    f"({today_iso}).\n\n"
                    "Today's RLP-weighted average will use the unweighted fallback."
                ),
                title="Krowi: RLP profile missing today \u2139\ufe0f",
                notification_id="krowi_rlp_today_missing",
            )

        # Subscribe to midnight — detect year rollover
        self._unsubs.append(
            async_track_time_change(hass, self._on_midnight, hour=0, minute=0, second=1)
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
        """At midnight: reload weights if the year has changed; pre-fetch next year from Dec 26."""
        if now.year != self._loaded_year:
            self._next_year_prefetch_done = False
            self._hass.async_create_task(self._async_reload_for_year(now.year))
        elif now.month == 12 and now.day >= 26 and not self._next_year_prefetch_done:
            self._hass.async_create_task(self._async_prefetch_next_year(now.year + 1))

    async def _async_reload_for_year(self, year: int) -> None:
        """Swap storage key and reload (from cache or download) for the new year."""
        _LOGGER.info("SynergridRLPStore: year changed to %d — reloading profile", year)
        key = _STORAGE_KEY_PATTERN.format(year=year)
        self._storage = Store(self._hass, _STORAGE_VERSION, key)
        loaded = await self._async_load(year, self._dso_name)
        today_iso = date.today().isoformat()
        if loaded and today_iso in self._weights:
            self._available = True
            self._loaded_year = year
            _LOGGER.info(
                "SynergridRLPStore: loaded %d days from storage for year %d",
                len(self._weights),
                year,
            )
            from homeassistant.components import persistent_notification  # noqa: PLC0415
            persistent_notification.async_dismiss(self._hass, "krowi_rlp_load_failed")
            persistent_notification.async_dismiss(self._hass, "krowi_rlp_today_missing")
            return
        await self._async_download_and_parse(year, self._dso_name, context="year rollover")
        if self._available:
            self._loaded_year = year
            if today_iso not in self._weights:
                from homeassistant.components import persistent_notification  # noqa: PLC0415
                persistent_notification.async_create(
                    self._hass,
                    (
                        f"RLP profile for {year} loaded after year rollover but does not "
                        f"contain today ({today_iso}).\n\n"
                        "Today's RLP-weighted average will use the unweighted fallback."
                    ),
                    title="Krowi: RLP profile missing today \u2139\ufe0f",
                    notification_id="krowi_rlp_today_missing",
                )

    async def _async_prefetch_next_year(self, year: int) -> None:
        """Try to pre-fetch and cache next year's profile (Dec 26–31).

        Sends a persistent HA notification on success (once per session) or
        on every failure.
        """
        from homeassistant.components import persistent_notification  # noqa: PLC0415

        _PREF_SUCCESS_ID = "krowi_rlp_prefetch_success"  # noqa: N806
        _PREF_FAILED_ID = "krowi_rlp_prefetch_failed"  # noqa: N806

        _LOGGER.debug("SynergridRLPStore: attempting pre-fetch for year %d", year)

        # Check if already cached for next year
        next_storage = Store(self._hass, _STORAGE_VERSION, _STORAGE_KEY_PATTERN.format(year=year))
        try:
            raw = await next_storage.async_load()
        except Exception:  # noqa: BLE001
            raw = None

        if (
            raw
            and isinstance(raw, dict)
            and raw.get("dso") == self._dso_name
            and isinstance(raw.get("weights"), dict)
            and raw["weights"]
        ):
            _LOGGER.info("SynergridRLPStore: year %d profile already cached", year)
            self._next_year_prefetch_done = True
            persistent_notification.async_dismiss(self._hass, _PREF_FAILED_ID)
            persistent_notification.async_create(
                self._hass,
                f"Year {year} RLP profile ({self._dso_name}) is ready in cache.",
                title="Krowi: RLP profile pre-fetched ✅",
                notification_id=_PREF_SUCCESS_ID,
            )
            return

        # Download
        url = _RLP_URL_PATTERN.format(year=year)
        session = async_get_clientsession(self._hass)
        try:
            async with session.get(url) as resp:
                resp.raise_for_status()
                data = await resp.read()
            weights = await self._hass.async_add_executor_job(
                _parse_xlsb, data, year, self._dso_name
            )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("SynergridRLPStore: pre-fetch for year %d failed: %s", year, exc)
            persistent_notification.async_create(
                self._hass,
                (
                    f"Failed to pre-fetch year {year} RLP profile "
                    f"({self._dso_name}): {exc}\n\n"
                    "Will retry at midnight. The profile may not be published yet."
                ),
                title="Krowi: RLP pre-fetch failed ⚠️",
                notification_id=_PREF_FAILED_ID,
            )
            return

        if not weights:
            _LOGGER.warning(
                "SynergridRLPStore: pre-fetch for year %d returned 0 days — not yet published",
                year,
            )
            persistent_notification.async_create(
                self._hass,
                (
                    f"Year {year} RLP profile downloaded but contained 0 days "
                    f"for DSO '{self._dso_name}'. "
                    "The file may not be published yet — will retry at midnight."
                ),
                title="Krowi: RLP pre-fetch incomplete ⚠️",
                notification_id=_PREF_FAILED_ID,
            )
            return

        # Persist to next year's storage key
        try:
            await next_storage.async_save({"dso": self._dso_name, "weights": weights})
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning(
                "SynergridRLPStore: failed to persist year %d pre-fetch: %s", year, exc
            )

        self._next_year_prefetch_done = True
        persistent_notification.async_dismiss(self._hass, _PREF_FAILED_ID)
        persistent_notification.async_create(
            self._hass,
            (
                f"Year {year} RLP profile ({self._dso_name}) "
                f"successfully pre-fetched and cached ({len(weights)} days)."
            ),
            title="Krowi: RLP profile pre-fetched ✅",
            notification_id=_PREF_SUCCESS_ID,
        )
        _LOGGER.info(
            "SynergridRLPStore: pre-fetched and cached year %d profile (%d days)",
            year,
            len(weights),
        )

    # -------------------------------------------------------------------------
    # Load / Download / Persist
    # -------------------------------------------------------------------------

    async def _async_load(self, year: int, dso_name: str) -> bool:
        """Load weights from HA Storage. Returns True if any data was loaded."""
        try:
            raw = await self._storage.async_load()
        except Exception as exc:
            _LOGGER.warning("SynergridRLPStore: failed to load from storage: %s", exc)
            return False

        if not isinstance(raw, dict):
            return False

        # New format: {"dso": "...", "weights": {...}}
        # Old (flat) format: {"2026-01-01": [...], ...} — discard if DSO key missing
        if raw.get("dso") != dso_name:
            _LOGGER.debug(
                "SynergridRLPStore: cached DSO '%s' != configured '%s' — discarding cache",
                raw.get("dso"),
                dso_name,
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

    async def _async_download_and_parse(self, year: int, dso_name: str, context: str = "startup") -> None:
        """Download and parse the .xlsb file for the given year."""
        from homeassistant.components import persistent_notification  # noqa: PLC0415

        _NOTIF_ID = "krowi_rlp_load_failed"  # noqa: N806
        _degraded = "unavailable" if context == "startup" else "falling back to unweighted means"  # noqa: N806
        _restart = " Restart HA to retry." if context == "startup" else ""  # noqa: N806
        url = _RLP_URL_PATTERN.format(year=year)
        session = async_get_clientsession(self._hass)
        try:
            async with session.get(url) as resp:
                resp.raise_for_status()
                data = await resp.read()
        except Exception as exc:
            _LOGGER.warning(
                "SynergridRLPStore: failed to download RLP profile for year %d: %s",
                year,
                exc,
            )
            self._available = False
            persistent_notification.async_create(
                self._hass,
                (
                    f"RLP profile for {year} could not be downloaded ({context}): {exc}\n\n"
                    f"RLP-weighted sensors are {_degraded}.{_restart}"
                ),
                title="Krowi: RLP profile unavailable \u26a0\ufe0f",
                notification_id=_NOTIF_ID,
            )
            return

        try:
            weights = await self._hass.async_add_executor_job(
                _parse_xlsb, data, year, dso_name
            )
        except Exception as exc:
            _LOGGER.warning(
                "SynergridRLPStore: failed to parse RLP profile for year %d: %s",
                year,
                exc,
            )
            self._available = False
            persistent_notification.async_create(
                self._hass,
                (
                    f"RLP profile for {year} downloaded but failed to parse ({context}): {exc}\n\n"
                    f"The file format may have changed. RLP-weighted sensors are {_degraded}.{_restart}"
                ),
                title="Krowi: RLP profile parse error \u26a0\ufe0f",
                notification_id=_NOTIF_ID,
            )
            return

        if not weights:
            _LOGGER.warning(
                "SynergridRLPStore: parsed 0 days for year %d — unexpected format",
                year,
            )
            self._available = False
            persistent_notification.async_create(
                self._hass,
                (
                    f"RLP profile for {year} downloaded but contained 0 days "
                    f"for DSO '{dso_name}' ({context}).\n\n"
                    "Check DSO configuration — the name may have changed in the Synergrid file."
                    + _restart
                ),
                title="Krowi: RLP profile empty \u26a0\ufe0f",
                notification_id=_NOTIF_ID,
            )
            return

        self._weights = weights
        self._available = True
        self._rlp_available_dates = set(weights.keys())
        self._dso_name = dso_name
        _LOGGER.debug(
            "SynergridRLPStore: downloaded and parsed %d days for year %d",
            len(weights),
            year,
        )

        # Dismiss any previous failure notification
        persistent_notification.async_dismiss(self._hass, _NOTIF_ID)

        # Persist to HA Storage
        await self._async_persist()

    async def _async_persist(self) -> None:
        """Save weights to HA Storage."""
        try:
            await self._storage.async_save(
                {"dso": self._dso_name, "weights": self._weights}
            )
        except Exception as exc:
            _LOGGER.warning("SynergridRLPStore: failed to save to storage: %s", exc)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def has_date(self, d: date) -> bool:
        """Return True iff weights are cached for date d."""
        return d.isoformat() in self._weights

    def get_weights(self, d: date) -> list[float] | None:
        """Return the weight list for date d, or None if unavailable."""
        return self._weights.get(d.isoformat())

    def is_rlp_date(self, d: date) -> bool:
        """Return True iff the weights for this date came from the RLP download (not fallback)."""
        return d.isoformat() in self._rlp_available_dates

    # -------------------------------------------------------------------------
    # Diagnostic actions (called by HA services)
    # -------------------------------------------------------------------------

    def action_store_state(self) -> dict:
        """Return a snapshot of the current in-memory store state."""
        sorted_dates = sorted(self._weights.keys())
        return {
            "available": self._available,
            "loaded_year": self._loaded_year,
            "dso": self._dso_name,
            "date_count": len(self._weights),
            "has_today": date.today().isoformat() in self._weights,
            "first_date": sorted_dates[0] if sorted_dates else None,
            "last_date": sorted_dates[-1] if sorted_dates else None,
        }

    async def async_action_test_fetch(self, year: int) -> dict:
        """Live download + parse for the given year. Does NOT modify store state."""
        url = _RLP_URL_PATTERN.format(year=year)
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
                "dso": self._dso_name,
                "http_status": http_status,
                "date_count": None,
                "has_today": None,
                "first_date": None,
                "last_date": None,
                "error": str(exc),
            }

        try:
            weights = await self._hass.async_add_executor_job(
                _parse_xlsb, data, year, self._dso_name
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "year": year,
                "dso": self._dso_name,
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
            "dso": self._dso_name,
            "http_status": http_status,
            "date_count": len(weights),
            "has_today": today_iso in weights,
            "first_date": sorted_dates[0] if sorted_dates else None,
            "last_date": sorted_dates[-1] if sorted_dates else None,
            "error": None if weights else f"Parsed 0 days for DSO '{self._dso_name}'",
        }
