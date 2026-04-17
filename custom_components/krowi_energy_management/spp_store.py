"""Synergrid SPP ex-ante electricity production profile store for Krowi Energy Management."""
from __future__ import annotations

import io
import logging
import xml.etree.ElementTree as ET
import zipfile
from datetime import date

from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore
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
            return

        _LOGGER.debug(
            "SynergridSPPStore: today (%s) not in cache — downloading for year %d",
            today_iso,
            year,
        )
        await self._async_download_and_parse(year)

    async def async_stop(self) -> None:
        """Stop the store — no-op (no subscriptions to clean up)."""

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

    async def _async_download_and_parse(self, year: int) -> None:
        """Download and parse the .xlsx file for the given year."""
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
            return

        if not weights:
            _LOGGER.warning(
                "SynergridSPPStore: parsed 0 days for year %d — unexpected format",
                year,
            )
            self._available = False
            return

        self._weights = weights
        self._available = True
        _LOGGER.debug(
            "SynergridSPPStore: downloaded and parsed %d days for year %d",
            len(weights),
            year,
        )

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
