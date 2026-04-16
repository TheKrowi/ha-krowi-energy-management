"""Synergrid RLP0N electricity profile store for Krowi Energy Management."""
from __future__ import annotations

import io
import logging
from datetime import date, datetime

from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore
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
            return

        # Need to download
        _LOGGER.debug(
            "SynergridRLPStore: today (%s) not in cache — downloading for year %d",
            today_iso,
            year,
        )
        await self._async_download_and_parse(year, dso_name)

    async def async_stop(self) -> None:
        """Stop the store — no-op (no subscriptions to clean up)."""

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

    async def _async_download_and_parse(self, year: int, dso_name: str) -> None:
        """Download and parse the .xlsb file for the given year."""
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
            return

        if not weights:
            _LOGGER.warning(
                "SynergridRLPStore: parsed 0 days for year %d — unexpected format",
                year,
            )
            self._available = False
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
