"""Krowi Energy Management integration setup."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue, async_delete_issue

from .const import CONF_DOMAIN_TYPE, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.NUMBER, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry and register the entity-rename watcher."""
    # Clear any pre-existing rename issue from a previous run
    async_delete_issue(hass, DOMAIN, f"entity_renamed_{entry.entry_id}")

    # Register entity registry listener to detect renames
    @callback
    def _on_entity_registry_updated(event) -> None:
        action = event.data.get("action")
        if action != "update":
            return
        if "entity_id" not in event.data.get("changes", {}):
            return

        # Check if the renamed entity belongs to this entry
        registry = er.async_get(hass)
        entity_entry = registry.async_get(event.data["entity_id"])
        if entity_entry is None or entity_entry.config_entry_id != entry.entry_id:
            return

        domain_type = entry.data.get(CONF_DOMAIN_TYPE, "unknown")
        async_create_issue(
            hass,
            DOMAIN,
            f"entity_renamed_{entry.entry_id}",
            severity=IssueSeverity.WARNING,
            is_fixable=False,
            translation_key="entity_renamed",
            translation_placeholders={"domain_type": domain_type},
        )

    unsub = hass.bus.async_listen("entity_registry_updated", _on_entity_registry_updated)
    hass.data.setdefault(DOMAIN, {})[f"unsub_registry_{entry.entry_id}"] = unsub

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unsubscribe the entity registry listener
    unsub = hass.data.get(DOMAIN, {}).pop(f"unsub_registry_{entry.entry_id}", None)
    if unsub:
        unsub()

    # Clear the Repairs issue
    async_delete_issue(hass, DOMAIN, f"entity_renamed_{entry.entry_id}")

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
