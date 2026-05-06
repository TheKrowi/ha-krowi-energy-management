"""Synergrid SPP ex-ante electricity production profile store for Krowi Energy Management."""
from __future__ import annotations

import io
import logging
import xml.etree.ElementTree as ET
import zipfile
from datetime import date, datetime

from homeassistant.core import HomeAssistant, callback  # type: ignore
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore
from homeassistant.helpers.event import async_track_time_change  # type: ignore
from homeassistant.helpers.storage import Store  # type: ignore

_LOGGER = logging.getLogger(__name__)

_SPP_URL_PATTERN = (
    "https://www.synergrid.be/images/downloads/SLP-RLP-SPP/"
    "{year}/SPP_ex-ante_and_ex-post_{year}.xlsx"
)
_STORAGE_KEY_PATTERN = "krowi_energy_management_spp_{year}"
_STORAGE_VERSION = 1
_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_SPP_SHEET_PREFIX = "SPP_ex-ante_"


def _parse_xlsx(data: bytes, year: int) -> dict[str, list[float]]:
    """Parse the Synergrid SPP ex-ante .xlsx file in a worker thread.

    Returns a dict mapping ISO date strings (YYYY-MM-DD) to a list of
    96 weight floats (SPPExanteBE column) in chronological QH order.
    DST spring-forward days skip H=2 but still have 96 rows.
    """
    result: dict[str, list[float]] = {}

    with zipfile.ZipFile(io.BytesIO(data)) as z:
        # Locate the SPP_ex-ante_{year} sheet via workbook.xml + rels
        wb_tree = ET.parse(z.open("xl/workbook.xml"))
        rels_tree = ET.parse(z.open("xl/_rels/workbook.xml.rels"))

        # Build rId → sheet filename map
        rid_to_file: dict[str, str] = {}
        for r in rels_tree.findall(
            ".//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"
        ):
            rid_to_file[r.get("Id")] = r.get("Target")

        # Find rId for the SPP ex-ante sheet
        sheet_rid: str | None = None
        for sheet in wb_tree.findall(".//x:sheet", _NS):
            name = sheet.get("name", "")
            if name.startswith(_SPP_SHEET_PREFIX):
                sheet_rid = sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
                break

        if sheet_rid is None:
            _LOGGER.warning(
                "SynergridSPPStore: sheet starting with '%s' not found in workbook",
                _SPP_SHEET_PREFIX,
            )
            return result

        sheet_path = "xl/" + rid_to_file.get(sheet_rid, "")
        if sheet_path == "xl/":
            _LOGGER.warning("SynergridSPPStore: could not resolve sheet path for rId %s", sheet_rid)
            return result

        ws_tree = ET.parse(z.open(sheet_path))
        rows = ws_tree.findall(".//x:row", _NS)

    if not rows:
        _LOGGER.warning("SynergridSPPStore: sheet '%s' is empty", sheet_path)
        return result

    # Row 0 is the header: [UTC, Year, Month, Day, Hour, Min, SPPExanteBE]
    # Data rows: col indices 1=Year, 2=Month, 3=Day, 6=SPPExanteBE (all numeric, no shared strings)
    for row in rows[1:]:
        cells = row.findall("x:c", _NS)
        # Guard: need at least 7 cells
        if len(cells) < 7:
            continue
        try:
            v_year = cells[1].find("x:v", _NS)
            v_month = cells[2].find("x:v", _NS)
            v_day = cells[3].find("x:v", _NS)
            v_spp = cells[6].find("x:v", _NS)
            if v_year is None or v_month is None or v_day is None or v_spp is None:
                continue
            key = f"{int(float(v_year.text))}-{int(float(v_month.text)):02d}-{int(float(v_day.text)):02d}"
            result.setdefault(key, []).append(float(v_spp.text))
        except (ValueError, TypeError, AttributeError):
            pass

    return result


class SynergridSPPStore:
    """Downloads, caches and serves the annual Synergrid SPP ex-ante electricity weights."""

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
    # Lifecycle
    # -------------------------------------------------------------------------

    async def async_start(self, hass: HomeAssistant) -> None:
        """Start the store: load from HA Storage or download if needed."""
        self._hass = hass
        year = date.today().year
        self._loaded_year = year
        key = _STORAGE_KEY_PATTERN.format(year=year)
        self._storage = Store(hass, _STORAGE_VERSION, key)

        loaded = await self._async_load(year)
        today_iso = date.today().isoformat()

        if loaded and today_iso in self._weights:
            self._available = True
            _LOGGER.debug(
                "SynergridSPPStore: loaded %d days from storage for year %d",
                len(self._weights),
                year,
            )
            from homeassistant.components import persistent_notification  # noqa: PLC0415
            persistent_notification.async_dismiss(self._hass, "krowi_spp_load_failed")
            persistent_notification.async_dismiss(self._hass, "krowi_spp_today_missing")
            return

        _LOGGER.debug(
            "SynergridSPPStore: today (%s) not in cache — downloading for year %d",
            today_iso,
            year,
        )
        await self._async_download_and_parse(year, context="startup")

        if self._available and today_iso not in self._weights:
            from homeassistant.components import persistent_notification  # noqa: PLC0415
            persistent_notification.async_create(
                self._hass,
                (
                    f"SPP profile for {year} was loaded but does not contain today "
                    f"({today_iso}).\n\n"
                    "Today's SPP-weighted average will use the unweighted fallback."
                ),
                title="Krowi: SPP profile missing today \u2139\ufe0f",
                notification_id="krowi_spp_today_missing",
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
        _LOGGER.info("SynergridSPPStore: year changed to %d — reloading profile", year)
        key = _STORAGE_KEY_PATTERN.format(year=year)
        self._storage = Store(self._hass, _STORAGE_VERSION, key)
        loaded = await self._async_load(year)
        today_iso = date.today().isoformat()
        if loaded and today_iso in self._weights:
            self._available = True
            self._loaded_year = year
            _LOGGER.info(
                "SynergridSPPStore: loaded %d days from storage for year %d",
                len(self._weights),
                year,
            )
            from homeassistant.components import persistent_notification  # noqa: PLC0415
            persistent_notification.async_dismiss(self._hass, "krowi_spp_load_failed")
            persistent_notification.async_dismiss(self._hass, "krowi_spp_today_missing")
            return
        await self._async_download_and_parse(year, context="year rollover")
        if self._available:
            self._loaded_year = year
            if today_iso not in self._weights:
                from homeassistant.components import persistent_notification  # noqa: PLC0415
                persistent_notification.async_create(
                    self._hass,
                    (
                        f"SPP profile for {year} loaded after year rollover but does not "
                        f"contain today ({today_iso}).\n\n"
                        "Today's SPP-weighted average will use the unweighted fallback."
                    ),
                    title="Krowi: SPP profile missing today \u2139\ufe0f",
                    notification_id="krowi_spp_today_missing",
                )

    async def _async_prefetch_next_year(self, year: int) -> None:
        """Try to pre-fetch and cache next year's profile (Dec 26–31).

        Sends a persistent HA notification on success (once per session) or
        on every failure.
        """
        from homeassistant.components import persistent_notification  # noqa: PLC0415

        _PREF_SUCCESS_ID = "krowi_spp_prefetch_success"  # noqa: N806
        _PREF_FAILED_ID = "krowi_spp_prefetch_failed"  # noqa: N806

        _LOGGER.debug("SynergridSPPStore: attempting pre-fetch for year %d", year)

        # Check if already cached for next year
        next_storage = Store(self._hass, _STORAGE_VERSION, _STORAGE_KEY_PATTERN.format(year=year))
        try:
            raw = await next_storage.async_load()
        except Exception:  # noqa: BLE001
            raw = None

        if (
            raw
            and isinstance(raw, dict)
            and any(isinstance(v, list) and v for v in raw.values())
        ):
            _LOGGER.info("SynergridSPPStore: year %d profile already cached", year)
            self._next_year_prefetch_done = True
            persistent_notification.async_dismiss(self._hass, _PREF_FAILED_ID)
            persistent_notification.async_create(
                self._hass,
                f"Year {year} SPP profile is ready in cache.",
                title="Krowi: SPP profile pre-fetched ✅",
                notification_id=_PREF_SUCCESS_ID,
            )
            return

        # Download
        url = _SPP_URL_PATTERN.format(year=year)
        session = async_get_clientsession(self._hass)
        try:
            async with session.get(url) as resp:
                resp.raise_for_status()
                data = await resp.read()
            weights = await self._hass.async_add_executor_job(_parse_xlsx, data, year)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("SynergridSPPStore: pre-fetch for year %d failed: %s", year, exc)
            persistent_notification.async_create(
                self._hass,
                (
                    f"Failed to pre-fetch year {year} SPP profile: {exc}\n\n"
                    "Will retry at midnight. The profile may not be published yet."
                ),
                title="Krowi: SPP pre-fetch failed ⚠️",
                notification_id=_PREF_FAILED_ID,
            )
            return

        if not weights:
            _LOGGER.warning(
                "SynergridSPPStore: pre-fetch for year %d returned 0 days — not yet published",
                year,
            )
            persistent_notification.async_create(
                self._hass,
                (
                    f"Year {year} SPP profile downloaded but contained 0 days. "
                    "The file may not be published yet — will retry at midnight."
                ),
                title="Krowi: SPP pre-fetch incomplete ⚠️",
                notification_id=_PREF_FAILED_ID,
            )
            return

        # Persist to next year's storage key
        try:
            await next_storage.async_save(weights)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning(
                "SynergridSPPStore: failed to persist year %d pre-fetch: %s", year, exc
            )

        self._next_year_prefetch_done = True
        persistent_notification.async_dismiss(self._hass, _PREF_FAILED_ID)
        persistent_notification.async_create(
            self._hass,
            f"Year {year} SPP profile successfully pre-fetched and cached ({len(weights)} days).",
            title="Krowi: SPP profile pre-fetched ✅",
            notification_id=_PREF_SUCCESS_ID,
        )
        _LOGGER.info(
            "SynergridSPPStore: pre-fetched and cached year %d profile (%d days)",
            year,
            len(weights),
        )

    # -------------------------------------------------------------------------
    # Load / Download / Persist
    # -------------------------------------------------------------------------

    async def _async_load(self, year: int) -> bool:
        """Load weights from HA Storage. Returns True if any data was loaded."""
        try:
            raw = await self._storage.async_load()
        except Exception as exc:
            _LOGGER.warning("SynergridSPPStore: failed to load from storage: %s", exc)
            return False

        if not isinstance(raw, dict):
            return False

        weights: dict[str, list[float]] = {}
        for key, val in raw.items():
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
        """Download and parse the .xlsx file for the given year."""
        from homeassistant.components import persistent_notification  # noqa: PLC0415

        _NOTIF_ID = "krowi_spp_load_failed"  # noqa: N806
        _degraded = "unavailable" if context == "startup" else "falling back to unweighted means"  # noqa: N806
        _restart = " Restart HA to retry." if context == "startup" else ""  # noqa: N806
        url = _SPP_URL_PATTERN.format(year=year)
        session = async_get_clientsession(self._hass)
        try:
            async with session.get(url) as resp:
                resp.raise_for_status()
                data = await resp.read()
        except Exception as exc:
            _LOGGER.warning(
                "SynergridSPPStore: failed to download SPP profile for year %d: %s",
                year,
                exc,
            )
            self._available = False
            persistent_notification.async_create(
                self._hass,
                (
                    f"SPP profile for {year} could not be downloaded ({context}): {exc}\n\n"
                    f"SPP-weighted sensors are {_degraded}.{_restart}"
                ),
                title="Krowi: SPP profile unavailable \u26a0\ufe0f",
                notification_id=_NOTIF_ID,
            )
            return

        try:
            weights = await self._hass.async_add_executor_job(
                _parse_xlsx, data, year
            )
        except Exception as exc:
            _LOGGER.warning(
                "SynergridSPPStore: failed to parse SPP profile for year %d: %s",
                year,
                exc,
            )
            self._available = False
            persistent_notification.async_create(
                self._hass,
                (
                    f"SPP profile for {year} downloaded but failed to parse ({context}): {exc}\n\n"
                    f"The file format may have changed. SPP-weighted sensors are {_degraded}.{_restart}"
                ),
                title="Krowi: SPP profile parse error \u26a0\ufe0f",
                notification_id=_NOTIF_ID,
            )
            return

        if not weights:
            _LOGGER.warning(
                "SynergridSPPStore: parsed 0 days for year %d — unexpected format",
                year,
            )
            self._available = False
            persistent_notification.async_create(
                self._hass,
                (
                    f"SPP profile for {year} downloaded but contained 0 days ({context}).\n\n"
                    "The file format may have changed. SPP-weighted sensors are "
                    + _degraded + "." + _restart
                ),
                title="Krowi: SPP profile empty \u26a0\ufe0f",
                notification_id=_NOTIF_ID,
            )
            return

        self._weights = weights
        self._available = True
        _LOGGER.debug(
            "SynergridSPPStore: downloaded and parsed %d days for year %d",
            len(weights),
            year,
        )

        # Dismiss any previous failure notification
        persistent_notification.async_dismiss(self._hass, _NOTIF_ID)

        await self._async_persist()

    async def _async_persist(self) -> None:
        """Save weights to HA Storage."""
        try:
            await self._storage.async_save(self._weights)
        except Exception as exc:
            _LOGGER.warning("SynergridSPPStore: failed to save to storage: %s", exc)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def has_date(self, d: date) -> bool:
        """Return True iff weights are cached for date d."""
        return d.isoformat() in self._weights

    def get_weights(self, d: date) -> list[float] | None:
        """Return the weight list for date d, or None if unavailable."""
        return self._weights.get(d.isoformat())

    # -------------------------------------------------------------------------
    # Diagnostic actions (called by HA services)
    # -------------------------------------------------------------------------

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
        url = _SPP_URL_PATTERN.format(year=year)
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
            weights = await self._hass.async_add_executor_job(
                _parse_xlsx, data, year
            )
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
