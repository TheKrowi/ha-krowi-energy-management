"""Synergrid RLP0N electricity profile store for Krowi Energy Management."""
from __future__ import annotations

import io
import logging
from datetime import date

from .synergrid_weights_store import _SynergridWeightsStore

_LOGGER = logging.getLogger(__name__)

_RLP_URL_PATTERN = (
    "https://www.synergrid.be/images/downloads/SLP-RLP-SPP/"
    "{year}/RLP0N%20{year}%20Electricity%20all%20DSOs.xlsb"
)


def _parse_xlsb(data: bytes, year: int, dso_name: str) -> dict[str, list[float]]:
    """Parse the Synergrid RLP0N all-DSOs .xlsb file in a worker thread.

    Returns a dict mapping ISO date strings (YYYY-MM-DD) to a list of
    96 (+/-4 for DST) weight floats for the specified DSO.
    """
    import pyxlsb  # type: ignore  # noqa: PLC0415

    result: dict[str, list[float]] = {}
    with pyxlsb.open_workbook(io.BytesIO(data)) as wb:
        with wb.get_sheet("RLP96UbyDGO") as sheet:
            rows = list(sheet.rows())

    # Row 1 (index 1): DGO names starting at col 7
    if len(rows) < 4:
        _LOGGER.warning("SynergridRLPStore: unexpected file format -- too few rows")
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


class SynergridRLPStore(_SynergridWeightsStore):
    """Downloads, caches and serves the annual Synergrid RLP0N electricity weights."""

    def __init__(self) -> None:
        super().__init__()
        self._dso_name: str = ""
        self._rlp_available_dates: set[str] = set()

    # -------------------------------------------------------------------------
    # Abstract property/method implementations
    # -------------------------------------------------------------------------

    @property
    def _label(self) -> str:
        return "RLP"

    def _url_for_year(self, year: int) -> str:
        return _RLP_URL_PATTERN.format(year=year)

    def _storage_key_for_year(self, year: int) -> str:
        return f"krowi_energy_management_rlp_{year}"

    def _parse_file(self, data: bytes, year: int) -> dict[str, list[float]]:
        return _parse_xlsb(data, year, self._dso_name)

    def _build_envelope(self, year: int, weights: dict) -> dict:
        return {"dso": self._dso_name, "weights": weights}

    def _cache_valid(self, raw: dict, year: int) -> bool:
        return raw.get("dso") == self._dso_name

    # -------------------------------------------------------------------------
    # Optional hook overrides
    # -------------------------------------------------------------------------

    def _profile_description(self) -> str:
        return f"RLP ({self._dso_name})" if self._dso_name else "RLP"

    def _on_weights_downloaded(self, weights: dict) -> None:
        self._rlp_available_dates = set(weights.keys())

    def _on_loaded_from_cache(self) -> None:
        self._rlp_available_dates = set(self._weights.keys())

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    async def async_start(self, hass, dso_name: str) -> None:
        """Start the store with the given DSO name."""
        self._dso_name = dso_name
        await self._async_start(hass)

    def is_rlp_date(self, d: date) -> bool:
        """Return True if the given date has real RLP weights (not just fallback)."""
        return d.isoformat() in self._rlp_available_dates

    def action_store_state(self) -> dict:
        state = super().action_store_state()
        state["dso"] = self._dso_name
        return state

    async def async_action_test_fetch(self, year: int) -> dict:
        """Live download + parse for the given year. Does NOT modify store state."""
        result = await super().async_action_test_fetch(year)
        result["dso"] = self._dso_name
        return result
