"""Krowi Energy Management integration setup."""
from __future__ import annotations

import logging

import voluptuous as vol  # type: ignore

from homeassistant.config_entries import ConfigEntry # type: ignore
from homeassistant.const import Platform # type: ignore
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback # type: ignore
from homeassistant.helpers import config_validation as cv, entity_registry as er # type: ignore
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue, async_delete_issue # type: ignore

from .const import (
    ATRIAS_SUBSCRIPTION_KEY,
    CONF_ATRIAS_SUBSCRIPTION_KEY,
    CONF_BATTERY_CONTROL_MODE_SWITCH,
    CONF_BATTERY_FORCE_MODE_SELECT,
    CONF_BATTERY_FORCIBLE_CHARGE_POWER_NUMBER,
    CONF_BATTERY_FORCIBLE_DISCHARGE_POWER_NUMBER,
    CONF_BATTERY_TARGET_CHARGE_POWER_SENSOR,
    CONF_BATTERY_TARGET_DISCHARGE_POWER_SENSOR,
    CONF_BATTERY_THRESHOLD,
    CONF_DOMAIN_TYPE,
    CONF_ELECTRICITY_DSO,
    CONF_FX_RATE_ENTITY,
    CONF_GAS_METER_ENTITY,
    CONF_GOS_ZONE,
    CONF_LOW_PRICE_CUTOFF,
    DEFAULT_BATTERY_THRESHOLD,
    DEFAULT_ELECTRICITY_DSO,
    DEFAULT_GAS_METER_ENTITY,
    DEFAULT_GOS_ZONE,
    DEFAULT_LOW_PRICE_CUTOFF,
    DOMAIN,
    DOMAIN_TYPE_BATTERY,
    DOMAIN_TYPE_ELECTRICITY,
    DOMAIN_TYPE_ELECTRICITY_SUPPLIER,
    DOMAIN_TYPE_GAS,
)
from .battery_manager import BatteryManager
from .nordpool_store import NordpoolBeStore
from .rlp_store import SynergridRLPStore
from .spp_store import SynergridSPPStore
from .ttf_dam_store import TtfDamStore
from .gcv_store import GcvStore

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.NUMBER, Platform.SENSOR, Platform.SWITCH]

VERSION = 3


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entries from older versions."""
    _LOGGER.debug("Migrating config entry '%s' from version %s", entry.entry_id, entry.version)

    if entry.version > VERSION:
        return False

    if entry.version == 1:
        new_data = dict(entry.data)
        if new_data.get(CONF_DOMAIN_TYPE) == DOMAIN_TYPE_ELECTRICITY:
            for key in (CONF_FX_RATE_ENTITY, "unit", "current_price_entity"):
                new_data.pop(key, None)
        hass.config_entries.async_update_entry(entry, data=new_data, version=2)
        _LOGGER.info("Migrated config entry '%s' to version 2", entry.entry_id)

    if entry.version == 2:
        new_data = dict(entry.data)
        if new_data.get(CONF_DOMAIN_TYPE) == DOMAIN_TYPE_GAS:
            new_data.pop("unit", None)
            new_data.pop("current_price_entity", None)
        hass.config_entries.async_update_entry(entry, data=new_data, version=3)
        _LOGGER.info("Migrated config entry '%s' to version 3", entry.entry_id)

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
        dso = effective.get(CONF_ELECTRICITY_DSO, DEFAULT_ELECTRICITY_DSO)
        rlp_store = SynergridRLPStore()
        await rlp_store.async_start(hass, dso_name=dso)
        hass.data.setdefault(DOMAIN, {})["rlp_store"] = rlp_store
        spp_store = SynergridSPPStore()
        await spp_store.async_start(hass)
        hass.data.setdefault(DOMAIN, {})["spp_store"] = spp_store
        store = NordpoolBeStore()
        hass.data.setdefault(DOMAIN, {})["nordpool_store"] = store
        await store.async_start(hass, low_price_cutoff, rlp_store, spp_store)
        _async_register_electricity_services(hass)

    # For gas entries, start the TTF DAM store and GCV store before platform setup
    if entry.data.get(CONF_DOMAIN_TYPE) == DOMAIN_TYPE_GAS:
        effective = {**entry.data, **entry.options}
        ttf_store = TtfDamStore()
        hass.data.setdefault(DOMAIN, {})["ttf_dam_store"] = ttf_store
        await ttf_store.async_start(hass)

        gos_zone = effective.get(CONF_GOS_ZONE, DEFAULT_GOS_ZONE)
        subscription_key = effective.get(CONF_ATRIAS_SUBSCRIPTION_KEY, ATRIAS_SUBSCRIPTION_KEY)
        gcv_store = GcvStore(gos_zone)
        hass.data.setdefault(DOMAIN, {})["gcv_store"] = gcv_store
        await gcv_store.async_start(hass, subscription_key=subscription_key)
        _async_register_gcv_services(hass)

    # For battery entries, start the battery manager before platform setup
    if entry.data.get(CONF_DOMAIN_TYPE) == DOMAIN_TYPE_BATTERY:
        effective = {**entry.data, **entry.options}
        manager_config = {
            CONF_BATTERY_CONTROL_MODE_SWITCH: effective.get(CONF_BATTERY_CONTROL_MODE_SWITCH),
            CONF_BATTERY_TARGET_CHARGE_POWER_SENSOR: effective.get(CONF_BATTERY_TARGET_CHARGE_POWER_SENSOR),
            CONF_BATTERY_TARGET_DISCHARGE_POWER_SENSOR: effective.get(CONF_BATTERY_TARGET_DISCHARGE_POWER_SENSOR),
            CONF_BATTERY_FORCIBLE_CHARGE_POWER_NUMBER: effective.get(CONF_BATTERY_FORCIBLE_CHARGE_POWER_NUMBER),
            CONF_BATTERY_FORCIBLE_DISCHARGE_POWER_NUMBER: effective.get(CONF_BATTERY_FORCIBLE_DISCHARGE_POWER_NUMBER),
            CONF_BATTERY_FORCE_MODE_SELECT: effective.get(CONF_BATTERY_FORCE_MODE_SELECT),
            CONF_BATTERY_THRESHOLD: effective.get(CONF_BATTERY_THRESHOLD, DEFAULT_BATTERY_THRESHOLD),
        }
        manager = BatteryManager(entry.entry_id, manager_config)
        hass.data.setdefault(DOMAIN, {})[f"battery_manager_{entry.entry_id}"] = manager
        await manager.async_start(hass)

    if entry.data.get(CONF_DOMAIN_TYPE) in (
        DOMAIN_TYPE_ELECTRICITY,
        DOMAIN_TYPE_GAS,
        DOMAIN_TYPE_ELECTRICITY_SUPPLIER,
        DOMAIN_TYPE_BATTERY,
    ):
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
        rlp_store = hass.data.get(DOMAIN, {}).pop("rlp_store", None)
        if rlp_store:
            await rlp_store.async_stop()
        spp_store = hass.data.get(DOMAIN, {}).pop("spp_store", None)
        if spp_store:
            await spp_store.async_stop()
        _async_unregister_electricity_services(hass)

    # Stop the TTF DAM store and GCV store for gas entries
    if entry.data.get(CONF_DOMAIN_TYPE) == DOMAIN_TYPE_GAS:
        store = hass.data.get(DOMAIN, {}).pop("ttf_dam_store", None)
        if store:
            await store.async_stop()
        gcv_store = hass.data.get(DOMAIN, {}).pop("gcv_store", None)
        if gcv_store:
            await gcv_store.async_stop()
        _async_unregister_gcv_services(hass)

    # Stop the battery manager for battery entries
    if entry.data.get(CONF_DOMAIN_TYPE) == DOMAIN_TYPE_BATTERY:
        manager = hass.data.get(DOMAIN, {}).pop(f"battery_manager_{entry.entry_id}", None)
        if manager:
            await manager.async_stop()

    # Unsubscribe the entity registry listener
    unsub = hass.data.get(DOMAIN, {}).pop(f"unsub_registry_{entry.entry_id}", None)
    if unsub:
        unsub()

    # Clear the Repairs issue
    async_delete_issue(hass, DOMAIN, f"entity_renamed_{entry.entry_id}")

    if entry.data.get(CONF_DOMAIN_TYPE) not in (
        DOMAIN_TYPE_ELECTRICITY,
        DOMAIN_TYPE_GAS,
        DOMAIN_TYPE_ELECTRICITY_SUPPLIER,
        DOMAIN_TYPE_BATTERY,
    ):
        return True
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


# ---------------------------------------------------------------------------
# GCV diagnostic services
# ---------------------------------------------------------------------------

_GCV_SERVICE_TEST_CONNECTION = "gcv_test_connection"
_GCV_SERVICE_TEST_FETCH = "gcv_test_fetch"
_GCV_SERVICE_STORE_STATE = "gcv_store_state"

_SCHEMA_GCV_TEST_FETCH = vol.Schema(
    {
        vol.Optional("year"): vol.All(vol.Coerce(int), vol.Range(min=2020, max=2040)),
        vol.Optional("month"): vol.All(vol.Coerce(int), vol.Range(min=1, max=12)),
    }
)


def _async_register_gcv_services(hass: HomeAssistant) -> None:
    """Register GCV diagnostic services (idempotent — skips if already registered)."""

    if hass.services.has_service(DOMAIN, _GCV_SERVICE_TEST_CONNECTION):
        return

    async def _test_connection(call: ServiceCall) -> dict:
        gcv_store: GcvStore | None = hass.data.get(DOMAIN, {}).get("gcv_store")
        if gcv_store is None:
            return {"ok": False, "error": "GCV store not initialised (no gas config entry)"}
        return await gcv_store.async_action_test_connection()

    async def _test_fetch(call: ServiceCall) -> dict:
        gcv_store: GcvStore | None = hass.data.get(DOMAIN, {}).get("gcv_store")
        if gcv_store is None:
            return {
                "ok": False,
                "target_month": None,
                "zone": None,
                "http_status": None,
                "gcv_value": None,
                "error": "GCV store not initialised (no gas config entry)",
            }
        from datetime import date  # noqa: PLC0415
        from dateutil.relativedelta import relativedelta  # type: ignore  # noqa: PLC0415

        data = call.data
        if "year" in data and "month" in data:
            year, month = int(data["year"]), int(data["month"])
        else:
            ref = date.today() - relativedelta(months=1)
            year, month = ref.year, ref.month
        return await gcv_store.async_action_test_fetch(year, month)

    def _store_state(call: ServiceCall) -> dict:
        gcv_store: GcvStore | None = hass.data.get(DOMAIN, {}).get("gcv_store")
        if gcv_store is None:
            return {
                "zone": None,
                "gcv": None,
                "data_is_fresh": False,
                "target_month": None,
                "history_count": 0,
                "history": {},
                "error": "GCV store not initialised (no gas config entry)",
            }
        return gcv_store.action_store_state()

    hass.services.async_register(
        DOMAIN,
        _GCV_SERVICE_TEST_CONNECTION,
        _test_connection,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        _GCV_SERVICE_TEST_FETCH,
        _test_fetch,
        schema=_SCHEMA_GCV_TEST_FETCH,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        _GCV_SERVICE_STORE_STATE,
        _store_state,
        supports_response=SupportsResponse.ONLY,
    )
    _LOGGER.debug("GCV diagnostic services registered")


def _async_unregister_gcv_services(hass: HomeAssistant) -> None:
    """Remove GCV diagnostic services when the gas entry is unloaded."""
    for service in (_GCV_SERVICE_TEST_CONNECTION, _GCV_SERVICE_TEST_FETCH, _GCV_SERVICE_STORE_STATE):
        hass.services.async_remove(DOMAIN, service)


# ---------------------------------------------------------------------------
# Electricity (RLP / SPP) diagnostic services
# ---------------------------------------------------------------------------

_ELEC_SERVICE_RLP_STORE_STATE = "rlp_store_state"
_ELEC_SERVICE_SPP_STORE_STATE = "spp_store_state"
_ELEC_SERVICE_RLP_TEST_FETCH = "rlp_test_fetch"
_ELEC_SERVICE_SPP_TEST_FETCH = "spp_test_fetch"

_SCHEMA_ELEC_TEST_FETCH = vol.Schema(
    {
        vol.Optional("year"): vol.All(vol.Coerce(int), vol.Range(min=2020, max=2040)),
    }
)


def _async_register_electricity_services(hass: HomeAssistant) -> None:
    """Register RLP / SPP diagnostic services (idempotent)."""

    if hass.services.has_service(DOMAIN, _ELEC_SERVICE_RLP_STORE_STATE):
        return

    def _rlp_store_state(call: ServiceCall) -> dict:
        rlp_store: SynergridRLPStore | None = hass.data.get(DOMAIN, {}).get("rlp_store")
        if rlp_store is None:
            return {"error": "RLP store not initialised (no electricity config entry)"}
        return rlp_store.action_store_state()

    def _spp_store_state(call: ServiceCall) -> dict:
        spp_store: SynergridSPPStore | None = hass.data.get(DOMAIN, {}).get("spp_store")
        if spp_store is None:
            return {"error": "SPP store not initialised (no electricity config entry)"}
        return spp_store.action_store_state()

    async def _rlp_test_fetch(call: ServiceCall) -> dict:
        rlp_store: SynergridRLPStore | None = hass.data.get(DOMAIN, {}).get("rlp_store")
        if rlp_store is None:
            return {"ok": False, "error": "RLP store not initialised (no electricity config entry)"}
        from datetime import date  # noqa: PLC0415
        year = int(call.data.get("year", date.today().year))
        return await rlp_store.async_action_test_fetch(year)

    async def _spp_test_fetch(call: ServiceCall) -> dict:
        spp_store: SynergridSPPStore | None = hass.data.get(DOMAIN, {}).get("spp_store")
        if spp_store is None:
            return {"ok": False, "error": "SPP store not initialised (no electricity config entry)"}
        from datetime import date  # noqa: PLC0415
        year = int(call.data.get("year", date.today().year))
        return await spp_store.async_action_test_fetch(year)

    hass.services.async_register(
        DOMAIN,
        _ELEC_SERVICE_RLP_STORE_STATE,
        _rlp_store_state,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        _ELEC_SERVICE_SPP_STORE_STATE,
        _spp_store_state,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        _ELEC_SERVICE_RLP_TEST_FETCH,
        _rlp_test_fetch,
        schema=_SCHEMA_ELEC_TEST_FETCH,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        _ELEC_SERVICE_SPP_TEST_FETCH,
        _spp_test_fetch,
        schema=_SCHEMA_ELEC_TEST_FETCH,
        supports_response=SupportsResponse.ONLY,
    )
    _LOGGER.debug("Electricity (RLP/SPP) diagnostic services registered")


def _async_unregister_electricity_services(hass: HomeAssistant) -> None:
    """Remove electricity diagnostic services when the electricity entry is unloaded."""
    for service in (
        _ELEC_SERVICE_RLP_STORE_STATE,
        _ELEC_SERVICE_SPP_STORE_STATE,
        _ELEC_SERVICE_RLP_TEST_FETCH,
        _ELEC_SERVICE_SPP_TEST_FETCH,
    ):
        hass.services.async_remove(DOMAIN, service)
