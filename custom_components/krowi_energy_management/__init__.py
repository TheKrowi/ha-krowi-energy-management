"""Krowi Energy Management integration setup."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry # type: ignore
from homeassistant.const import Platform # type: ignore
from homeassistant.core import HomeAssistant, callback # type: ignore
from homeassistant.helpers import entity_registry as er # type: ignore
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue, async_delete_issue # type: ignore

from .const import (
    CONF_CURRENT_PRICE_ENTITY,
    CONF_DOMAIN_TYPE,
    CONF_FX_RATE_ENTITY,
    CONF_LOW_PRICE_CUTOFF,
    CONF_UNIT,
    DEFAULT_LOW_PRICE_CUTOFF,
    DOMAIN,
    DOMAIN_TYPE_ELECTRICITY,
)
from .nordpool_store import NordpoolBeStore

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.NUMBER, Platform.SENSOR]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entries from older versions."""
    _LOGGER.debug("Migrating config entry '%s' from version %s", entry.entry_id, entry.version)

    if entry.version > 2:
        return False

    if entry.version == 1:
        new_data = dict(entry.data)
        if new_data.get(CONF_DOMAIN_TYPE) == DOMAIN_TYPE_ELECTRICITY:
            for key in (CONF_CURRENT_PRICE_ENTITY, CONF_FX_RATE_ENTITY, CONF_UNIT):
                new_data.pop(key, None)
        hass.config_entries.async_update_entry(entry, data=new_data, version=2)
        _LOGGER.info("Migrated config entry '%s' to version 2", entry.entry_id)

    return True


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

    # For electricity entries, start the Nord Pool BE store before platform setup
    if entry.data.get(CONF_DOMAIN_TYPE) == DOMAIN_TYPE_ELECTRICITY:
        effective = {**entry.data, **entry.options}
        low_price_cutoff = effective.get(CONF_LOW_PRICE_CUTOFF, DEFAULT_LOW_PRICE_CUTOFF)
        store = NordpoolBeStore()
        await store.async_start(hass, low_price_cutoff)
        hass.data.setdefault(DOMAIN, {})["nordpool_store"] = store

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Stop the Nord Pool store for electricity entries
    if entry.data.get(CONF_DOMAIN_TYPE) == DOMAIN_TYPE_ELECTRICITY:
        store = hass.data.get(DOMAIN, {}).pop("nordpool_store", None)
        if store:
            await store.async_stop()

    # Unsubscribe the entity registry listener
    unsub = hass.data.get(DOMAIN, {}).pop(f"unsub_registry_{entry.entry_id}", None)
    if unsub:
        unsub()

    # Clear the Repairs issue
    async_delete_issue(hass, DOMAIN, f"entity_renamed_{entry.entry_id}")

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
