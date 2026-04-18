"""Tests for custom_components.krowi_energy_management.gcv_store."""
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from dateutil.relativedelta import relativedelta

from custom_components.krowi_energy_management.gcv_store import GcvStore


def _make_store(zone: str = "H-zone") -> GcvStore:
    store = GcvStore(zone)
    store._hass = MagicMock()
    store._hass.async_create_task = MagicMock()
    store._store = AsyncMock()
    store._store.async_save = AsyncMock()
    return store


# ---------------------------------------------------------------------------
# _target_month (static)
# ---------------------------------------------------------------------------


def test_target_month_returnsOneCalendarMonthBefore():
    # Given / When
    actual = GcvStore._target_month(date(2026, 4, 17))

    # Then
    assert actual == (2026, 3)


def test_target_month_januaryReference_returnsPriorDecember():
    # Given / When
    actual = GcvStore._target_month(date(2026, 1, 15))

    # Then
    assert actual == (2025, 12)


# ---------------------------------------------------------------------------
# _last_12_targets (static)
# ---------------------------------------------------------------------------


def test_last_12_targets_returns12EntriesChronological():
    # Given / When
    with patch("custom_components.krowi_energy_management.gcv_store.date") as mock_date:
        mock_date.today.return_value = date(2026, 4, 17)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        actual = GcvStore._last_12_targets()

    # Then
    assert len(actual) == 12
    assert actual[0] == (2025, 4)
    assert actual[-1] == (2026, 3)


# ---------------------------------------------------------------------------
# _parse_zone_gcv
# ---------------------------------------------------------------------------


_CSV_TEMPLATE = (
    "Some header line\n"
    "GCVMonth,ARSName,GCVValue\n"
    "2026-03,H-zone,\"10,85\"\n"
    "2026-03,L-zone,\"9,50\"\n"
)


def test_parse_zone_gcv_zoneFound_returnsFloat():
    # Given
    store = _make_store(zone="H-zone")

    # When
    actual = store._parse_zone_gcv(_CSV_TEMPLATE, 2026, 3)

    # Then
    assert actual == pytest.approx(10.85)


def test_parse_zone_gcv_zoneNotFound_returnsNone():
    # Given
    store = _make_store(zone="X-zone")

    # When
    actual = store._parse_zone_gcv(_CSV_TEMPLATE, 2026, 3)

    # Then
    assert actual is None


def test_parse_zone_gcv_noCsvHeader_returnsNone():
    # Given
    store = _make_store(zone="H-zone")
    text_without_header = "just some text\nno csv here\n"

    # When
    actual = store._parse_zone_gcv(text_without_header, 2026, 3)

    # Then
    assert actual is None


def test_parse_zone_gcv_commaDecimalSeparator_parsesCorrectly():
    # Given
    store = _make_store(zone="H-zone")
    csv_with_comma = (
        "header\n"
        "GCVMonth,ARSName,GCVValue\n"
        '2026-03,H-zone,"10,85"\n'
    )

    # When
    actual = store._parse_zone_gcv(csv_with_comma, 2026, 3)

    # Then
    assert actual == pytest.approx(10.85)


# ---------------------------------------------------------------------------
# _refresh_gcv
# ---------------------------------------------------------------------------


def test_refresh_gcv_historyEmpty_setsNone():
    # Given
    store = _make_store()
    store._history = {}

    # When
    store._refresh_gcv()

    # Then
    assert store.gcv is None


def test_refresh_gcv_historyWithEntries_setsMostRecentValue():
    # Given
    store = _make_store()
    store._history = {"2026-02": 10.5, "2026-03": 11.2}

    # When
    store._refresh_gcv()

    # Then
    assert store.gcv == pytest.approx(11.2)


# ---------------------------------------------------------------------------
# _prune_history
# ---------------------------------------------------------------------------


def test_prune_history_moreThan12Entries_keepsNewest12():
    # Given
    store = _make_store()
    store._history = {f"2025-{m:02d}": float(m) for m in range(1, 14)}  # 13 entries

    # When
    store._prune_history()

    # Then
    assert len(store._history) == 12
    assert "2025-01" not in store._history  # oldest removed


def test_prune_history_exactly12Entries_noneRemoved():
    # Given
    store = _make_store()
    store._history = {f"2025-{m:02d}": float(m) for m in range(1, 13)}  # 12 entries

    # When
    store._prune_history()

    # Then
    assert len(store._history) == 12


# ---------------------------------------------------------------------------
# async_fetch_month
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_fetch_month_successfulResponse_returnsGcvValue():
    # Given
    store = _make_store(zone="H-zone")
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.text = AsyncMock(return_value=_CSV_TEMPLATE)
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    with patch(
        "custom_components.krowi_energy_management.gcv_store.async_get_clientsession",
        return_value=mock_session,
    ):
        # When
        actual = await store.async_fetch_month(2026, 3)

    # Then
    assert actual == pytest.approx(10.85)


@pytest.mark.asyncio
async def test_async_fetch_month_404Response_returnsNone():
    # Given
    store = _make_store()
    mock_resp = AsyncMock()
    mock_resp.status = 404
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    with patch(
        "custom_components.krowi_energy_management.gcv_store.async_get_clientsession",
        return_value=mock_session,
    ):
        # When
        actual = await store.async_fetch_month(2026, 3)

    # Then
    assert actual is None


@pytest.mark.asyncio
async def test_async_fetch_month_httpError_returnsNone():
    # Given
    store = _make_store()
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.raise_for_status = MagicMock(side_effect=Exception("network error"))
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    with patch(
        "custom_components.krowi_energy_management.gcv_store.async_get_clientsession",
        return_value=mock_session,
    ):
        # When
        actual = await store.async_fetch_month(2026, 3)

    # Then
    assert actual is None
