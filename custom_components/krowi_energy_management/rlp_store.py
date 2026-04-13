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
    "{year}/RLP0N%20{year}%20Electricity.xlsb"
)
_STORAGE_KEY_PATTERN = "krowi_energy_management_rlp_{year}"
_STORAGE_VERSION = 1


def _parse_xlsb(data: bytes, year: int) -> dict[str, list[float]]:
    """Parse the Synergrid RLP0N .xlsb file in a worker thread.

    Returns a dict mapping ISO date strings (YYYY-MM-DD) to a list of
    96 (±4 for DST) weight floats.
    """
    import pyxlsb  # type: ignore  # noqa: PLC0415

    result: dict[str, list[float]] = {}
    with pyxlsb.open_workbook(io.BytesIO(data)) as wb:
        # The profile sheet is the first non-hidden sheet; use the first sheet
        sheet_name = wb.sheets[0]
        with wb.get_sheet(sheet_name) as sheet:
            rows = list(sheet.rows())

    # Locate header row: find column index for each date and the weight rows.
    # The Synergrid format has:
    #   Row 1 (0-indexed row 0): date serial numbers in columns 1..N
    #   Row 2+: QH weights per date
    # Date serials are Excel/ODS date serials; pyxlsb returns them as floats.
    # We skip the first column (row label) and read subsequent columns as dates.

    if len(rows) < 2:
        _LOGGER.warning("SynergridRLPStore: unexpected file format — too few rows")
        return result

    header = rows[0]
    # Build list of (col_index, date) from header
    date_cols: list[tuple[int, date]] = []
    for col_idx, cell in enumerate(header):
        if col_idx == 0:
            continue
        val = cell.v if cell is not None else None
        if val is None:
            continue
        try:
            # Excel date serial: days since 1899-12-30
            d = date(1899, 12, 30) + __import__("datetime").timedelta(days=int(val))
            if d.year == year:
                date_cols.append((col_idx, d))
        except (ValueError, OverflowError):
            pass

    if not date_cols:
        _LOGGER.warning("SynergridRLPStore: no date columns found for year %d", year)
        return result

    # Collect weights per date column
    col_weights: dict[int, list[float]] = {ci: [] for ci, _ in date_cols}
    for row in rows[1:]:
        for col_idx, _ in date_cols:
            if col_idx < len(row) and row[col_idx] is not None:
                val = row[col_idx].v
                if val is not None:
                    try:
                        col_weights[col_idx].append(float(val))
                    except (ValueError, TypeError):
                        pass

    for col_idx, d in date_cols:
        weights = col_weights[col_idx]
        if weights:
            result[d.isoformat()] = weights

    return result


class SynergridRLPStore:
    """Downloads, caches and serves the annual Synergrid RLP0N electricity weights."""

    def __init__(self) -> None:
        self._hass: HomeAssistant | None = None
        self._weights: dict[str, list[float]] = {}  # ISO date → weight list
        self._storage: Store | None = None
        self._available: bool = False
        self._rlp_available_dates: set[str] = set()  # dates with real RLP weights

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

        # Attempt to load from storage
        loaded = await self._async_load(year)
        today_iso = date.today().isoformat()

        if loaded and today_iso in self._weights:
            self._available = True
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
            _LOGGER.warning("SynergridRLPStore: failed to load from storage: %s", exc)
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
                _parse_xlsb, data, year
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
            await self._storage.async_save(self._weights)
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
