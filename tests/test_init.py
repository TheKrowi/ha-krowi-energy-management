"""Tests for async_migrate_entry in krowi_energy_management/__init__.py."""
from unittest.mock import MagicMock

import pytest

from custom_components.krowi_energy_management import async_migrate_entry
from custom_components.krowi_energy_management.const import (
    CONF_DOMAIN_TYPE,
    CONF_FX_RATE_ENTITY,
    DOMAIN_TYPE_ELECTRICITY,
    DOMAIN_TYPE_GAS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hass() -> MagicMock:
    hass = MagicMock()
    hass.config_entries.async_update_entry = MagicMock()
    return hass


def _make_entry(version: int, data: dict) -> MagicMock:
    entry = MagicMock()
    entry.version = version
    entry.data = dict(data)
    entry.entry_id = "test_entry"
    return entry


# ---------------------------------------------------------------------------
# async_migrate_entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_migrateEntry_version1Electricity_removesObsoleteKeys():
    # Given: a v1 electricity entry with legacy keys
    hass = _make_hass()
    data = {
        CONF_DOMAIN_TYPE: DOMAIN_TYPE_ELECTRICITY,
        CONF_FX_RATE_ENTITY: "sensor.fx",
        "unit": "c€/kWh",
        "current_price_entity": "sensor.price",
    }
    entry = _make_entry(version=1, data=data)

    # When
    result = await async_migrate_entry(hass, entry)

    # Then
    assert result is True
    updated_data = hass.config_entries.async_update_entry.call_args_list[0].kwargs["data"]
    assert CONF_FX_RATE_ENTITY not in updated_data
    assert "unit" not in updated_data
    assert "current_price_entity" not in updated_data
    assert updated_data[CONF_DOMAIN_TYPE] == DOMAIN_TYPE_ELECTRICITY


@pytest.mark.asyncio
async def test_migrateEntry_version2Gas_removesObsoleteKeys():
    # Given: a v2 gas entry with legacy keys
    hass = _make_hass()
    data = {
        CONF_DOMAIN_TYPE: DOMAIN_TYPE_GAS,
        "unit": "c€/kWh",
        "current_price_entity": "sensor.gas",
    }
    entry = _make_entry(version=2, data=data)

    # When
    result = await async_migrate_entry(hass, entry)

    # Then
    assert result is True
    updated_data = hass.config_entries.async_update_entry.call_args_list[0].kwargs["data"]
    assert "unit" not in updated_data
    assert "current_price_entity" not in updated_data


@pytest.mark.asyncio
async def test_migrateEntry_versionNewerThanCurrent_returnsFalse():
    # Given: entry version newer than VERSION (3)
    hass = _make_hass()
    entry = _make_entry(version=99, data={CONF_DOMAIN_TYPE: DOMAIN_TYPE_ELECTRICITY})

    # When
    result = await async_migrate_entry(hass, entry)

    # Then
    assert result is False
    hass.config_entries.async_update_entry.assert_not_called()
