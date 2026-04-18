"""Tests for custom_components.krowi_energy_management.rlp_store."""
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.krowi_energy_management.rlp_store import SynergridRLPStore


def _make_store() -> SynergridRLPStore:
    store = SynergridRLPStore()
    store._hass = MagicMock()
    store._storage = AsyncMock()
    return store


# ---------------------------------------------------------------------------
# _async_load
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_load_rlp_validStorageWithMatchingDso_returnsTrue():
    # Given
    store = _make_store()
    store._storage.async_load = AsyncMock(return_value={
        "dso": "Fluvius Zenne-Dijle",
        "weights": {"2026-04-17": [0.5, 0.5]},
    })

    # When
    actual = await store._async_load(2026, "Fluvius Zenne-Dijle")

    # Then
    assert actual is True
    assert store._weights == {"2026-04-17": [0.5, 0.5]}


@pytest.mark.asyncio
async def test_async_load_rlp_dsoMismatch_returnsFalse():
    # Given
    store = _make_store()
    store._storage.async_load = AsyncMock(return_value={
        "dso": "Fluvius Antwerpen",
        "weights": {"2026-04-17": [0.5, 0.5]},
    })

    # When
    actual = await store._async_load(2026, "Fluvius Zenne-Dijle")

    # Then
    assert actual is False


@pytest.mark.asyncio
async def test_async_load_rlp_storageReturnsNone_returnsFalse():
    # Given
    store = _make_store()
    store._storage.async_load = AsyncMock(return_value=None)

    # When
    actual = await store._async_load(2026, "Fluvius Zenne-Dijle")

    # Then
    assert actual is False


@pytest.mark.asyncio
async def test_async_load_rlp_storageThrows_returnsFalse():
    # Given
    store = _make_store()
    store._storage.async_load = AsyncMock(side_effect=Exception("storage error"))

    # When
    actual = await store._async_load(2026, "Fluvius Zenne-Dijle")

    # Then
    assert actual is False


@pytest.mark.asyncio
async def test_async_load_rlp_emptyWeights_returnsFalse():
    # Given
    store = _make_store()
    store._storage.async_load = AsyncMock(return_value={
        "dso": "Fluvius Zenne-Dijle",
        "weights": {},
    })

    # When
    actual = await store._async_load(2026, "Fluvius Zenne-Dijle")

    # Then
    assert actual is False


# ---------------------------------------------------------------------------
# get_weights
# ---------------------------------------------------------------------------


def test_get_weights_dateInCache_returnsWeightList():
    # Given
    store = _make_store()
    store._weights = {"2026-04-17": [0.5, 0.5]}

    # When
    actual = store.get_weights(date(2026, 4, 17))

    # Then
    assert actual == [0.5, 0.5]


def test_get_weights_dateMissing_returnsNone():
    # Given
    store = _make_store()
    store._weights = {}

    # When
    actual = store.get_weights(date(2026, 4, 17))

    # Then
    assert actual is None


# ---------------------------------------------------------------------------
# has_date
# ---------------------------------------------------------------------------


def test_has_date_datePresent_returnsTrue():
    # Given
    store = _make_store()
    store._weights = {"2026-04-17": [0.5]}

    # When / Then
    assert store.has_date(date(2026, 4, 17)) is True


def test_has_date_dateAbsent_returnsFalse():
    # Given
    store = _make_store()
    store._weights = {}

    # When / Then
    assert store.has_date(date(2026, 4, 17)) is False
