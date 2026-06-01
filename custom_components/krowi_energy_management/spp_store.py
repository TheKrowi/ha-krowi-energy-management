"""Synergrid SPP ex-ante electricity production profile store for Krowi Energy Management."""
from __future__ import annotations

import io
import logging
import xml.etree.ElementTree as ET
import zipfile
from datetime import date

from .synergrid_weights_store import _SynergridWeightsStore

_LOGGER = logging.getLogger(__name__)

_SPP_URL_PATTERN = (
    "https://www.synergrid.be/images/downloads/SLP-RLP-SPP/"
    "{year}/SPP_ex-ante_and_ex-post_{year}.xlsx"
)
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

        # Build rId -> sheet filename map
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


class SynergridSPPStore(_SynergridWeightsStore):
    """Downloads, caches and serves the annual Synergrid SPP ex-ante electricity weights."""

    # -------------------------------------------------------------------------
    # Abstract property/method implementations
    # -------------------------------------------------------------------------

    @property
    def _label(self) -> str:
        return "SPP"

    def _url_for_year(self, year: int) -> str:
        return _SPP_URL_PATTERN.format(year=year)

    def _storage_key_for_year(self, year: int) -> str:
        return f"krowi_energy_management_spp_{year}"

    def _parse_file(self, data: bytes, year: int) -> dict[str, list[float]]:
        return _parse_xlsx(data, year)

    def _build_envelope(self, year: int, weights: dict) -> dict:
        return {"year": year, "weights": weights}

    def _cache_valid(self, raw: dict, year: int) -> bool:
        return raw.get("year") == year

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    async def async_start(self, hass) -> None:
        """Start the store."""
        await self._async_start(hass)
