"""Sensor platform entrypoint for Krowi Energy Management."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback  # type: ignore

from .const import CONF_DOMAIN_TYPE, DOMAIN_TYPE_ELECTRICITY, DOMAIN_TYPE_ELECTRICITY_SUPPLIER, DOMAIN_TYPE_GAS
from . import sensor_electricity, sensor_gas, sensor_supplier


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities for this config entry."""
    domain_type = entry.data[CONF_DOMAIN_TYPE]
    if domain_type == DOMAIN_TYPE_ELECTRICITY:
        await sensor_electricity.async_setup(hass, entry, async_add_entities)
    elif domain_type == DOMAIN_TYPE_GAS:
        await sensor_gas.async_setup(hass, entry, async_add_entities)
    elif domain_type == DOMAIN_TYPE_ELECTRICITY_SUPPLIER:
        await sensor_supplier.async_setup(hass, entry, async_add_entities)
