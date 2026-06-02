"""Tests for custom_components.krowi_energy_management.ttf_dam_store."""
from datetime import date, datetime, timezone, timedelta
from statistics import mean
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.krowi_energy_management.ttf_dam_store import TtfDamStore


def _make_store() -> TtfDamStore:
    store = TtfDamStore()
    store._hass = MagicMock()
    store._hass.async_create_task = MagicMock()
    store._storage = MagicMock()
    store._storage.async_save = AsyncMock()
    return store


def _ts_ms(d: date) -> int:
    """UTC Unix ms for midnight of a date (as the Elindus API uses)."""
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)


def _api_response(*entries: tuple[date, float]) -> dict:
    """Build a minimal Elindus API response from (date, EUR/MWh) pairs."""
    return {
        "dataSeries": {
            "data": [
                {"x": _ts_ms(d), "y": price, "name": d.strftime("%d/%m/%Y 00:00")}
                for d, price in entries
            ]
        }
    }


# ---------------------------------------------------------------------------
# async_fetch — buffer population
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_fetch_successfulResponseTodayDate_populatesBufferAndMarksFresh():
    # Given
    store = _make_store()
    today = date.today()
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = AsyncMock(return_value=_api_response((today, 450.0)))
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    with patch(
        "custom_components.krowi_energy_management.ttf_dam_store.async_get_clientsession",
        return_value=mock_session,
    ), patch("custom_components.krowi_energy_management.ttf_dam_store.async_dispatcher_send"):
        await store.async_fetch()

    # Then
    assert store.today_price == pytest.approx(45.0)  # 450 / 10
    assert store.data_is_fresh is True


@pytest.mark.asyncio
async def test_async_fetch_staleDate_bufferPopulatedButNotFresh():
    # Given
    store = _make_store()
    past = date.today() - timedelta(days=1)
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = AsyncMock(return_value=_api_response((past, 450.0)))
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    with patch(
        "custom_components.krowi_energy_management.ttf_dam_store.async_get_clientsession",
        return_value=mock_session,
    ), patch("custom_components.krowi_energy_management.ttf_dam_store.async_dispatcher_send"):
        await store.async_fetch()

    # Then — past date entered buffer but today is not in it
    assert store.today_price is None
    assert store.data_is_fresh is False
    assert past in store._daily_buffer


@pytest.mark.asyncio
async def test_async_fetch_multipleEntries_allMergedIntoBuffer():
    # Given
    store = _make_store()
    today = date.today()
    d1 = today - timedelta(days=2)
    d2 = today - timedelta(days=1)
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = AsyncMock(return_value=_api_response((d1, 400.0), (d2, 420.0), (today, 450.0)))
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    with patch(
        "custom_components.krowi_energy_management.ttf_dam_store.async_get_clientsession",
        return_value=mock_session,
    ), patch("custom_components.krowi_energy_management.ttf_dam_store.async_dispatcher_send"):
        await store.async_fetch()

    assert store._daily_buffer[d1] == pytest.approx(40.0)
    assert store._daily_buffer[d2] == pytest.approx(42.0)
    assert store._daily_buffer[today] == pytest.approx(45.0)


@pytest.mark.asyncio
async def test_async_fetch_httpError_bufferUnchangedAndDispatches():
    # Given
    store = _make_store()
    store._daily_buffer = {date.today(): 5.0}
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock(side_effect=Exception("network error"))
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    with patch(
        "custom_components.krowi_energy_management.ttf_dam_store.async_get_clientsession",
        return_value=mock_session,
    ), patch(
        "custom_components.krowi_energy_management.ttf_dam_store.async_dispatcher_send"
    ) as mock_dispatch:
        await store.async_fetch()

    assert store._daily_buffer == {date.today(): 5.0}  # unchanged
    mock_dispatch.assert_called_once()


@pytest.mark.asyncio
async def test_async_fetch_malformedJson_bufferUnchangedAndDispatches():
    # Given
    store = _make_store()
    store._daily_buffer = {date.today(): 3.0}
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = AsyncMock(return_value={"wrong": "data"})
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    with patch(
        "custom_components.krowi_energy_management.ttf_dam_store.async_get_clientsession",
        return_value=mock_session,
    ), patch(
        "custom_components.krowi_energy_management.ttf_dam_store.async_dispatcher_send"
    ) as mock_dispatch:
        await store.async_fetch()

    assert store._daily_buffer == {date.today(): 3.0}  # unchanged
    mock_dispatch.assert_called_once()


@pytest.mark.asyncio
async def test_async_fetch_nullDataSeries_bufferUnchangedAndDispatches():
    """Regression: if dataSeries.data is null the signal must still fire."""
    # Given
    store = _make_store()
    store._daily_buffer = {date.today(): 3.0}
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = AsyncMock(return_value={"dataSeries": {"data": None}})
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    with patch(
        "custom_components.krowi_energy_management.ttf_dam_store.async_get_clientsession",
        return_value=mock_session,
    ), patch(
        "custom_components.krowi_energy_management.ttf_dam_store.async_dispatcher_send"
    ) as mock_dispatch:
        await store.async_fetch()

    assert store._daily_buffer == {date.today(): 3.0}  # unchanged
    mock_dispatch.assert_called_once()


@pytest.mark.asyncio
async def test_async_fetch_emptyDataSeries_bufferUnchanged():
    # Given
    store = _make_store()
    store._daily_buffer = {date.today(): 7.0}
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = AsyncMock(return_value={"dataSeries": {"data": []}})
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    with patch(
        "custom_components.krowi_energy_management.ttf_dam_store.async_get_clientsession",
        return_value=mock_session,
    ), patch("custom_components.krowi_energy_management.ttf_dam_store.async_dispatcher_send"):
        await store.async_fetch()

    assert store.today_price == pytest.approx(7.0)  # buffer entry preserved


# ---------------------------------------------------------------------------
# _fetch_in_flight guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_fetch_inFlight_secondCallReturnsImmediately():
    # Given
    store = _make_store()
    store._fetch_in_flight = True
    mock_session = MagicMock()

    with patch(
        "custom_components.krowi_energy_management.ttf_dam_store.async_get_clientsession",
        return_value=mock_session,
    ):
        await store.async_fetch()

    # No HTTP call should be made when guard is active
    mock_session.get.assert_not_called()


# ---------------------------------------------------------------------------
# rolling_average and month_average properties
# ---------------------------------------------------------------------------


def test_rolling_average_multipleEntries_returnsMean():
    # Given
    store = _make_store()
    today = date.today()
    store._daily_buffer = {
        today - timedelta(days=2): 4.0,
        today - timedelta(days=1): 5.0,
        today: 6.0,
    }

    # Then
    assert store.rolling_average == pytest.approx(mean([4.0, 5.0, 6.0]))


def test_rolling_average_emptyBuffer_returnsNone():
    store = _make_store()
    assert store.rolling_average is None


def test_month_average_onlyThisMonthEntries_returnsMean():
    # Given
    store = _make_store()
    today = date.today()
    first = today.replace(day=1)
    second = first + timedelta(days=1) if first != today else first
    store._daily_buffer = {
        first: 4.0,
        second: 6.0,
    }

    # Then — only entries from 1st of month onwards
    expected = mean([4.0, 6.0]) if first != second else 4.0
    assert store.month_average == pytest.approx(expected)


def test_month_average_entriesSpanMonthBoundary_onlyCurrentMonthCounted():
    # Given
    store = _make_store()
    today = date.today()
    first_of_month = today.replace(day=1)
    last_month_day = first_of_month - timedelta(days=1)
    store._daily_buffer = {
        last_month_day: 3.0,  # last month — excluded
        first_of_month: 5.0,  # this month — included
    }

    assert store.month_average == pytest.approx(5.0)


def test_month_average_emptyBuffer_returnsNone():
    store = _make_store()
    assert store.month_average is None


# ---------------------------------------------------------------------------
# data_is_fresh
# ---------------------------------------------------------------------------


def test_data_is_fresh_todayInBuffer_returnsTrue():
    store = _make_store()
    store._daily_buffer = {date.today(): 5.0}
    assert store.data_is_fresh is True


def test_data_is_fresh_todayNotInBuffer_returnsFalse():
    store = _make_store()
    store._daily_buffer = {}
    assert store.data_is_fresh is False


# ---------------------------------------------------------------------------
# Buffer persistence — load from Storage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_load_buffer_validStorage_populatesBuffer():
    # Given
    store = _make_store()
    store._storage.async_load = AsyncMock(return_value={"2026-05-01": 4.5, "2026-05-02": 5.0})

    # When
    await store._async_load_buffer()

    # Then
    assert store._daily_buffer == {date(2026, 5, 1): 4.5, date(2026, 5, 2): 5.0}


@pytest.mark.asyncio
async def test_async_load_buffer_invalidStorage_emptyBuffer():
    store = _make_store()
    store._storage.async_load = AsyncMock(return_value=None)
    await store._async_load_buffer()
    assert store._daily_buffer == {}


@pytest.mark.asyncio
async def test_async_load_buffer_storageError_emptyBuffer():
    store = _make_store()
    store._storage.async_load = AsyncMock(side_effect=Exception("storage error"))
    await store._async_load_buffer()
    assert store._daily_buffer == {}


# ---------------------------------------------------------------------------
# _trim_buffer
# ---------------------------------------------------------------------------


def test_trim_buffer_removesEntriesOlderThanOneMonth():
    # Given
    store = _make_store()
    today = date.today()
    from dateutil.relativedelta import relativedelta
    cutoff = today - relativedelta(months=1)
    old_date = cutoff - timedelta(days=1)
    recent_date = cutoff + timedelta(days=1)
    store._daily_buffer = {old_date: 1.0, recent_date: 2.0}

    # When
    store._trim_buffer()

    # Then
    assert old_date not in store._daily_buffer
    assert recent_date in store._daily_buffer


# ---------------------------------------------------------------------------
# _on_midnight
# ---------------------------------------------------------------------------


def test_on_midnight_schedulesFetch():
    # Given
    store = _make_store()

    # When
    store._on_midnight(datetime.now(timezone.utc))

    # Then
    store._hass.async_create_task.assert_called_once()


# ---------------------------------------------------------------------------
# _on_tick
# ---------------------------------------------------------------------------


def test_on_tick_notFresh_schedulesFetch():
    # Given — buffer empty so data_is_fresh = False
    store = _make_store()
    store._daily_buffer = {}

    # When
    store._on_tick(datetime.now(timezone.utc))

    # Then
    store._hass.async_create_task.assert_called_once()


def test_on_tick_dataFresh_doesNotScheduleFetch():
    # Given — today in buffer so data_is_fresh = True
    store = _make_store()
    store._daily_buffer = {date.today(): 5.0}

    # When
    store._on_tick(datetime.now(timezone.utc))

    # Then
    store._hass.async_create_task.assert_not_called()


# ---------------------------------------------------------------------------
# Timezone: Unix ms → local date via dt_utils.as_local
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_fetch_timestampConversion_usesLocalDate():
    """Verify that the UTC midnight timestamp for 2026-06-02 is stored under
    the correct local date key (not shifted to a different date).

    With as_local = identity (UTC == local in the test stub), the midnight UTC
    timestamp maps to 2026-06-02. The key in the buffer must be a real date object,
    not a MagicMock (regression guard for the as_local stub returning MagicMock).
    """
    # Given
    store = _make_store()
    target_date = date(2026, 6, 2)
    ts_ms = _ts_ms(target_date)
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = AsyncMock(return_value={"dataSeries": {"data": [{"x": ts_ms, "y": 450.0}]}})
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    with patch(
        "custom_components.krowi_energy_management.ttf_dam_store.async_get_clientsession",
        return_value=mock_session,
    ), patch("custom_components.krowi_energy_management.ttf_dam_store.async_dispatcher_send"):
        await store.async_fetch()

    # Then: target_date is a key in the buffer and it is a real date (not MagicMock)
    assert target_date in store._daily_buffer
    assert isinstance(list(store._daily_buffer.keys())[0], date)
    assert store._daily_buffer[target_date] == pytest.approx(45.0)

