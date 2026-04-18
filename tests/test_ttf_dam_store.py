"""Tests for custom_components.krowi_energy_management.ttf_dam_store."""
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.krowi_energy_management.ttf_dam_store import TtfDamStore


def _make_store() -> TtfDamStore:
    store = TtfDamStore()
    store._hass = MagicMock()
    store._hass.async_create_task = MagicMock()
    return store


def _api_response(today_price: float = 45.0, average_price: float = 52.0, use_today: bool = True) -> dict:
    """Build a minimal valid Elindus API response."""
    target_date = date.today() if use_today else date(2026, 4, 16)
    ts_ms = int(datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc).timestamp() * 1000)
    return {
        "statistics": {"averagePrice": average_price},
        "dataSeries": {
            "data": [{"x": ts_ms, "y": today_price, "name": target_date.strftime("%d/%m/%Y 00:00")}]
        },
    }


# ---------------------------------------------------------------------------
# async_fetch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_fetch_successfulResponseTodayDate_setsPropertiesAndMarksFresh():
    # Given
    store = _make_store()
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = AsyncMock(return_value=_api_response(today_price=450.0, average_price=529.0, use_today=True))
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    with patch(
        "custom_components.krowi_energy_management.ttf_dam_store.async_get_clientsession",
        return_value=mock_session,
    ), patch("custom_components.krowi_energy_management.ttf_dam_store.async_dispatcher_send"):
        # When
        await store.async_fetch()

    # Then
    assert store.today_price == pytest.approx(45.0)   # 450 / 10
    assert store.average == pytest.approx(52.9)        # 529 / 10
    assert store.data_is_fresh is True


@pytest.mark.asyncio
async def test_async_fetch_successfulResponseStaleDate_setsPropertiesNotFresh():
    # Given
    store = _make_store()
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = AsyncMock(return_value=_api_response(use_today=False))  # yesterday's data
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    with patch(
        "custom_components.krowi_energy_management.ttf_dam_store.async_get_clientsession",
        return_value=mock_session,
    ), patch("custom_components.krowi_energy_management.ttf_dam_store.async_dispatcher_send"):
        # When
        await store.async_fetch()

    # Then
    assert store.today_price is not None
    assert store.data_is_fresh is False


@pytest.mark.asyncio
async def test_async_fetch_httpError_keepsOldValuesAndDispatches():
    # Given
    store = _make_store()
    store._today_price = 5.0  # pre-existing value
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
        # When
        await store.async_fetch()

    # Then
    assert store.today_price == 5.0  # unchanged
    mock_dispatch.assert_called_once()


@pytest.mark.asyncio
async def test_async_fetch_malformedJson_keepsOldValuesAndDispatches():
    # Given
    store = _make_store()
    store._average = 3.0
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
        # When
        await store.async_fetch()

    # Then
    assert store.average == 3.0  # unchanged
    mock_dispatch.assert_called_once()


@pytest.mark.asyncio
async def test_async_fetch_emptyDataSeries_keepsOldValues():
    # Given
    store = _make_store()
    store._today_price = 7.0
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = AsyncMock(return_value={
        "statistics": {"averagePrice": 50.0},
        "dataSeries": {"data": []},  # empty — entries[-1] will raise IndexError
    })
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    with patch(
        "custom_components.krowi_energy_management.ttf_dam_store.async_get_clientsession",
        return_value=mock_session,
    ), patch("custom_components.krowi_energy_management.ttf_dam_store.async_dispatcher_send"):
        # When
        await store.async_fetch()

    # Then
    assert store.today_price == 7.0  # unchanged


# ---------------------------------------------------------------------------
# _on_midnight
# ---------------------------------------------------------------------------


def test_on_midnight_setsDataIsStaleAndSchedulesFetch():
    # Given
    store = _make_store()
    store._data_is_fresh = True

    # When
    store._on_midnight(datetime.now(timezone.utc))

    # Then
    assert store.data_is_fresh is False
    store._hass.async_create_task.assert_called_once()


# ---------------------------------------------------------------------------
# _on_tick
# ---------------------------------------------------------------------------


def test_on_tick_dataNotFresh_schedulesFetch():
    # Given
    store = _make_store()
    store._data_is_fresh = False

    # When
    store._on_tick(datetime.now(timezone.utc))

    # Then
    store._hass.async_create_task.assert_called_once()


def test_on_tick_dataFresh_doesNotScheduleFetch():
    # Given
    store = _make_store()
    store._data_is_fresh = True

    # When
    store._on_tick(datetime.now(timezone.utc))

    # Then
    store._hass.async_create_task.assert_not_called()
