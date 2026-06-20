"""Switch platform entry point for Krowi Energy Management."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback  # type: ignore

from .const import CONF_DOMAIN_TYPE, DOMAIN_TYPE_BATTERY
from . import switch_battery


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities for this config entry."""
    domain_type = entry.data[CONF_DOMAIN_TYPE]
    if domain_type == DOMAIN_TYPE_BATTERY:
        await switch_battery.async_setup(hass, entry, async_add_entities)
