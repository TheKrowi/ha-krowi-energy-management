"""Tests for custom_components.krowi_energy_management.nordpool_store."""
from datetime import date, datetime, timedelta, timezone
from statistics import mean
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from dateutil.relativedelta import relativedelta

from custom_components.krowi_energy_management.nordpool_store import NordpoolBeStore


def _make_store() -> NordpoolBeStore:
    """Return a NordpoolBeStore with _hass pre-set to a MagicMock."""
    store = NordpoolBeStore()
    store._hass = MagicMock()
    store._hass.async_create_task = MagicMock()
    return store


def _make_slot(start: datetime, value: float) -> dict:
    return {
        "start": start,
        "end": start + timedelta(minutes=15),
        "value": value,
    }


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# _async_fetch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_fetch_successfulResponse_returnsSlotList():
    # Given
    store = _make_store()
    api_response = {
        "multiAreaEntries": [
            {
                "deliveryStart": "2026-04-17T00:00:00+00:00",
                "deliveryEnd": "2026-04-17T00:15:00+00:00",
                "entryPerArea": {"BE": 500.0},
            }
        ]
    }
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = AsyncMock(return_value=api_response)
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    with patch(
        "custom_components.krowi_energy_management.nordpool_store.async_get_clientsession",
        return_value=mock_session,
    ):
        # When
        actual = await store._async_fetch("2026-04-17")

    # Then
    assert actual is not None
    assert len(actual) == 1
    assert actual[0]["value"] == pytest.approx(50.0)  # 500 / 10


@pytest.mark.asyncio
async def test_async_fetch_httpError_returnsNone():
    # Given
    store = _make_store()
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock(side_effect=Exception("503"))
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    with patch(
        "custom_components.krowi_energy_management.nordpool_store.async_get_clientsession",
        return_value=mock_session,
    ), patch(
        "custom_components.krowi_energy_management.nordpool_store.async_dispatcher_send"
    ):
        # When
        actual = await store._async_fetch("2026-04-17")

    # Then
    assert actual is None


@pytest.mark.asyncio
async def test_async_fetch_malformedJson_returnsNone():
    # Given
    store = _make_store()
    api_response = {"unexpected_key": []}  # missing multiAreaEntries
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = AsyncMock(return_value=api_response)
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    with patch(
        "custom_components.krowi_energy_management.nordpool_store.async_get_clientsession",
        return_value=mock_session,
    ), patch(
        "custom_components.krowi_energy_management.nordpool_store.async_dispatcher_send"
    ):
        # When
        actual = await store._async_fetch("2026-04-17")

    # Then
    assert actual is None


@pytest.mark.asyncio
async def test_async_fetch_missingBeArea_returnsNone():
    # Given
    store = _make_store()
    api_response = {
        "multiAreaEntries": [
            {
                "deliveryStart": "2026-04-17T00:00:00+00:00",
                "deliveryEnd": "2026-04-17T00:15:00+00:00",
                "entryPerArea": {"NL": 500.0},  # no BE key
            }
        ]
    }
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = AsyncMock(return_value=api_response)
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    with patch(
        "custom_components.krowi_energy_management.nordpool_store.async_get_clientsession",
        return_value=mock_session,
    ), patch(
        "custom_components.krowi_energy_management.nordpool_store.async_dispatcher_send"
    ):
        # When
        actual = await store._async_fetch("2026-04-17")

    # Then
    assert actual is None


# ---------------------------------------------------------------------------
# _update_current_price
# ---------------------------------------------------------------------------


def test_update_currentPrice_nowWithinSlot_setsPriceToSlotValue():
    # Given
    store = _make_store()
    now = datetime.now(timezone.utc)
    store._data_today = [_make_slot(now - timedelta(minutes=5), 12.34)]

    # When
    store._update_current_price()

    # Then
    assert store.current_price == pytest.approx(12.34)


def test_update_currentPrice_nowOutsideAllSlots_setsPriceToNone():
    # Given
    store = _make_store()
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    store._data_today = [_make_slot(yesterday, 9.0)]  # slot in the past, no active slot

    # When
    store._update_current_price()

    # Then
    assert store.current_price is None


def test_update_currentPrice_noData_setsPriceToNone():
    # Given
    store = _make_store()
    store._data_today = []

    # When
    store._update_current_price()

    # Then
    assert store.current_price is None


# ---------------------------------------------------------------------------
# average property
# ---------------------------------------------------------------------------


def test_average_noDataToday_returnsNone():
    # Given
    store = _make_store()
    store._data_today = []

    # When / Then
    assert store.average is None


def test_average_slotsPresent_returnsMeanRoundedTo5dp():
    # Given
    store = _make_store()
    now = datetime.now(timezone.utc)
    store._data_today = [
        _make_slot(now, 10.0),
        _make_slot(now + timedelta(minutes=15), 20.0),
    ]

    # When
    actual = store.average

    # Then
    assert actual == pytest.approx(15.0)


# ---------------------------------------------------------------------------
# monthly_average property
# ---------------------------------------------------------------------------


def test_monthly_average_noTodayData_returnsNone():
    # Given
    store = _make_store()
    store._data_today = []

    # When / Then
    assert store.monthly_average is None


def test_monthly_average_bufferEmpty_returnsTodayAverage():
    # Given
    store = _make_store()
    now = datetime.now(timezone.utc)
    store._data_today = [_make_slot(now, 5.0)]
    store._daily_avg_buffer = {}

    # When
    actual = store.monthly_average

    # Then
    assert actual == pytest.approx(5.0)


def test_monthly_average_bufferWithEntries_returnsMeanOfBufferAndToday():
    # Given
    store = _make_store()
    now = datetime.now(timezone.utc)
    yesterday = date.today() - timedelta(days=1)
    store._data_today = [_make_slot(now, 7.0)]
    store._daily_avg_buffer = {yesterday: 3.0}

    # When
    actual = store.monthly_average

    # Then
    assert actual == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# low_price property
# ---------------------------------------------------------------------------


def test_low_price_currentPriceBelowCutoff_returnsTrue():
    # Given
    store = _make_store()
    now = datetime.now(timezone.utc)
    store._data_today = [_make_slot(now - timedelta(minutes=1), 3.0)]
    store._update_current_price()
    store._data_today = [_make_slot(now - timedelta(minutes=1), 10.0)]  # drive average to 10
    store._low_price_cutoff = 0.5

    # When / Then
    # current_price = 3.0, average via property reads _data_today = [10.0], cutoff = 0.5
    # 3.0 < 10.0 * 0.5 = 5.0 → True
    store._current_price = 3.0
    store._data_today = [_make_slot(now - timedelta(minutes=1), 10.0)]
    assert store.low_price is True


def test_low_price_currentPriceAboveCutoff_returnsFalse():
    # Given
    store = _make_store()
    now = datetime.now(timezone.utc)
    store._current_price = 8.0
    store._data_today = [_make_slot(now - timedelta(minutes=1), 10.0)]
    store._low_price_cutoff = 0.5
    # 8.0 < 10.0 * 0.5 = 5.0 → False

    # When / Then
    assert store.low_price is False


def test_low_price_currentPriceNone_returnsNone():
    # Given
    store = _make_store()
    store._current_price = None

    # When / Then
    assert store.low_price is None


# ---------------------------------------------------------------------------
# _compute_rlp_avg
# ---------------------------------------------------------------------------


def test_compute_rlp_avg_noSlots_returnsZero():
    # Given
    store = _make_store()

    # When
    actual = store._compute_rlp_avg(date.today(), [])

    # Then
    assert actual == 0.0


def test_compute_rlp_avg_noRlpStore_returnsUnweightedMean():
    # Given
    store = _make_store()
    store._rlp_store = None
    now = datetime.now(timezone.utc)
    slots = [_make_slot(now, 10.0), _make_slot(now + timedelta(minutes=15), 20.0)]

    # When
    actual = store._compute_rlp_avg(date.today(), slots)

    # Then
    assert actual == pytest.approx(15.0)


def test_compute_rlp_avg_weightsCountMismatch_returnsUnweightedMean():
    # Given
    store = _make_store()
    mock_rlp = MagicMock()
    mock_rlp.get_weights.return_value = [1.0, 2.0, 3.0]  # 3 weights for 2 slots
    store._rlp_store = mock_rlp
    now = datetime.now(timezone.utc)
    slots = [_make_slot(now, 10.0), _make_slot(now + timedelta(minutes=15), 30.0)]

    # When
    actual = store._compute_rlp_avg(date.today(), slots)

    # Then
    assert actual == pytest.approx(20.0)  # plain mean fallback


def test_compute_rlp_avg_validWeights_returnsWeightedMean():
    # Given
    store = _make_store()
    mock_rlp = MagicMock()
    mock_rlp.get_weights.return_value = [3.0, 1.0]
    store._rlp_store = mock_rlp
    now = datetime.now(timezone.utc)
    slots = [_make_slot(now, 10.0), _make_slot(now + timedelta(minutes=15), 30.0)]

    # When
    actual = store._compute_rlp_avg(date.today(), slots)

    # Then
    # (10*3 + 30*1) / (3+1) = 60/4 = 15.0
    assert actual == pytest.approx(15.0)


def test_compute_rlp_avg_zeroTotalWeight_returnsUnweightedMean():
    # Given
    store = _make_store()
    mock_rlp = MagicMock()
    mock_rlp.get_weights.return_value = [0.0, 0.0]
    store._rlp_store = mock_rlp
    now = datetime.now(timezone.utc)
    slots = [_make_slot(now, 10.0), _make_slot(now + timedelta(minutes=15), 30.0)]

    # When
    actual = store._compute_rlp_avg(date.today(), slots)

    # Then
    assert actual == pytest.approx(20.0)  # plain mean fallback


# ---------------------------------------------------------------------------
# _trim_buffer
# ---------------------------------------------------------------------------


def test_trim_buffer_entriesOlderThanOneMonth_removed():
    # Given
    store = _make_store()
    old_date = date.today() - relativedelta(months=1) - timedelta(days=1)
    recent_date = date.today() - timedelta(days=1)
    store._daily_avg_buffer = {old_date: 5.0, recent_date: 6.0}
    store._daily_rlp_buffer = {old_date: 5.0}
    store._daily_spp_buffer = {}

    # When
    store._trim_buffer()

    # Then
    assert old_date not in store._daily_avg_buffer
    assert recent_date in store._daily_avg_buffer


def test_trim_buffer_allEntriesWithinWindow_noneRemoved():
    # Given
    store = _make_store()
    recent_date = date.today() - timedelta(days=1)
    store._daily_avg_buffer = {recent_date: 6.0}
    store._daily_rlp_buffer = {}
    store._daily_spp_buffer = {}

    # When
    store._trim_buffer()

    # Then
    assert recent_date in store._daily_avg_buffer


# ---------------------------------------------------------------------------
# _snapshot_today
# ---------------------------------------------------------------------------


def test_snapshot_today_noData_doesNotSnapshot():
    # Given
    store = _make_store()
    store._data_today = []
    store._hass.async_create_task = MagicMock()

    # When
    store._snapshot_today()

    # Then
    assert store._daily_avg_buffer == {}


def test_snapshot_today_withData_writesYesterdayEntry():
    # Given
    store = _make_store()
    now = datetime.now(timezone.utc)
    store._data_today = [_make_slot(now - timedelta(minutes=1), 12.5)]
    store._rlp_store = None
    store._spp_store = None
    store._storage = MagicMock()
    store._rlp_storage = MagicMock()
    store._spp_storage = MagicMock()
    store._hass.async_create_task = MagicMock()

    # When
    store._snapshot_today()

    # Then
    yesterday = date.today() - timedelta(days=1)
    assert yesterday in store._daily_avg_buffer
    assert store._daily_avg_buffer[yesterday] == pytest.approx(12.5)


# ---------------------------------------------------------------------------
# _async_load_buffer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_load_buffer_validStoredData_populatesBuffer():
    # Given
    store = _make_store()
    store._storage = AsyncMock()
    store._storage.async_load = AsyncMock(return_value={"2026-04-16": "5.0"})

    # When
    await store._async_load_buffer()

    # Then
    assert store._daily_avg_buffer == {date(2026, 4, 16): 5.0}


@pytest.mark.asyncio
async def test_async_load_buffer_storageReturnsNone_setsEmptyBuffer():
    # Given
    store = _make_store()
    store._storage = AsyncMock()
    store._storage.async_load = AsyncMock(return_value=None)

    # When
    await store._async_load_buffer()

    # Then
    assert store._daily_avg_buffer == {}


@pytest.mark.asyncio
async def test_async_load_buffer_storageThrows_setsEmptyBuffer():
    # Given
    store = _make_store()
    store._storage = AsyncMock()
    store._storage.async_load = AsyncMock(side_effect=Exception("disk error"))

    # When
    await store._async_load_buffer()

    # Then
    assert store._daily_avg_buffer == {}


@pytest.mark.asyncio
async def test_async_load_buffer_malformedEntries_skipsInvalid():
    # Given
    store = _make_store()
    store._storage = AsyncMock()
    store._storage.async_load = AsyncMock(
        return_value={"bad-date": "5.0", "2026-04-16": "not_float"}
    )

    # When
    await store._async_load_buffer()

    # Then
    assert store._daily_avg_buffer == {}


# ---------------------------------------------------------------------------
# price_percent_to_average property
# ---------------------------------------------------------------------------


def test_price_percent_to_average_zeroAverage_returnsNone():
    # Given
    store = _make_store()
    store._current_price = 5.0
    now = datetime.now(timezone.utc)
    store._data_today = [_make_slot(now - timedelta(minutes=1), 0.0)]  # average = 0

    # When / Then
    assert store.price_percent_to_average is None


def test_price_percent_to_average_validValues_returnsRoundedRatio():
    # Given
    store = _make_store()
    store._current_price = 3.0
    now = datetime.now(timezone.utc)
    store._data_today = [_make_slot(now - timedelta(minutes=1), 10.0)]  # average = 10

    # When
    actual = store.price_percent_to_average

    # Then
    assert actual == pytest.approx(0.3)
