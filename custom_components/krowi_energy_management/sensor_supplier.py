"""Electricity-supplier-domain sensor entities for Krowi Energy Management."""
from __future__ import annotations

from homeassistant.components.sensor import SensorStateClass  # type: ignore
from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.core import HomeAssistant, callback  # type: ignore
from homeassistant.helpers.device_registry import DeviceInfo  # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback  # type: ignore
from homeassistant.helpers.dispatcher import async_dispatcher_connect  # type: ignore

from .const import (
    CONF_SUPPLIER_LABEL,
    CONF_SUPPLIER_SLUG,
    DOMAIN,
    ELECTRICITY_SUPPLIER_CATALOG,
    LANG_EN,
    NAMES,
    SIGNAL_NORDPOOL_UPDATE,
    UNIT_ELECTRICITY,
    UID_ELECTRICITY_SURCHARGE_RATE,
    UID_ELECTRICITY_VAT,
)
from .sensor_base import KrowiSensor, _resolve_entity_id
from .utils import get_language, safe_float_state


# ---------------------------------------------------------------------------
# Electricity supplier price sensors
# ---------------------------------------------------------------------------

class ElectricitySupplierImportPriceSensor(KrowiSensor):
    """Supplier-specific electricity import price in c€/kWh (incl. VAT)."""

    _attr_icon = "mdi:currency-eur"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UNIT_ELECTRICITY

    def __init__(self, hass, entry_id, slug, catalog_params, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._slug = slug
        self._params = catalog_params
        uid = f"electricity_{slug}_import_price"
        self._attr_unique_id = uid
        self.entity_id = f"sensor.{uid}"
        self._attr_name = NAMES.get(
            ("electricity_supplier_import_price", language),
            NAMES[("electricity_supplier_import_price", LANG_EN)],
        )

    def _get_store(self):
        return self.hass.data.get(DOMAIN, {}).get("nordpool_store")

    def _subscribe_listeners(self) -> None:
        watch = []
        surcharge_id = _resolve_entity_id(self.hass, "sensor", UID_ELECTRICITY_SURCHARGE_RATE)
        if surcharge_id:
            watch.append(surcharge_id)
        vat_id = _resolve_entity_id(self.hass, "number", UID_ELECTRICITY_VAT)
        if vat_id:
            watch.append(vat_id)
        if watch:
            self._track(watch, self._handle_state_change)

    @callback
    def _handle_state_change(self, event) -> None:
        self._update()

    @callback
    def _update(self) -> None:
        store = self._get_store()
        if store is None or store.monthly_average_rlp is None:
            self._attr_native_value = None
            self._attr_available = False
            self.async_write_ha_state()
            return

        epex_rlp = store.monthly_average_rlp
        multiplier = self._params["epex_multiplier"]
        offset = self._params["epex_offset_cEur_kwh"]

        surcharge_id = _resolve_entity_id(self.hass, "sensor", UID_ELECTRICITY_SURCHARGE_RATE)
        surcharge = safe_float_state(self.hass, surcharge_id) if surcharge_id else 0.0
        if surcharge is None:
            surcharge = 0.0

        vat_id = _resolve_entity_id(self.hass, "number", UID_ELECTRICITY_VAT)
        vat = safe_float_state(self.hass, vat_id) if vat_id else 0.0
        if vat is None:
            vat = 0.0

        result = (epex_rlp * multiplier + offset + surcharge) * (1 + vat / 100)
        self._attr_native_value = round(result, 5)
        self._attr_available = True
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub_listeners.append(
            async_dispatcher_connect(self.hass, SIGNAL_NORDPOOL_UPDATE, self._update)
        )
        self._update()


class ElectricitySupplierImportPriceEurSensor(KrowiSensor):
    """Supplier-specific electricity import price in EUR/kWh (incl. VAT)."""

    _attr_icon = "mdi:currency-eur"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "EUR/kWh"

    def __init__(self, hass, entry_id, slug, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._slug = slug
        self._source_uid = f"electricity_{slug}_import_price"
        uid = f"electricity_{slug}_import_price_eur"
        self._attr_unique_id = uid
        self.entity_id = f"sensor.{uid}"
        self._attr_name = NAMES.get(
            ("electricity_supplier_import_price_eur", language),
            NAMES[("electricity_supplier_import_price_eur", LANG_EN)],
        )

    def _subscribe_listeners(self) -> None:
        source_id = _resolve_entity_id(self.hass, "sensor", self._source_uid)
        if source_id:
            self._track([source_id], self._handle_state_change)

    @callback
    def _handle_state_change(self, event) -> None:
        self._update()

    def _update(self) -> None:
        source_id = _resolve_entity_id(self.hass, "sensor", self._source_uid)
        val = safe_float_state(self.hass, source_id) if source_id else None
        if val is None:
            self._attr_native_value = None
            self._attr_available = False
        else:
            self._attr_native_value = round(val / 100, 7)
            self._attr_available = True
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._update()


class ElectricitySupplierExportPriceSensor(KrowiSensor):
    """Supplier-specific electricity export price in c€/kWh (BTW-vrij)."""

    _attr_icon = "mdi:currency-eur"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UNIT_ELECTRICITY

    def __init__(self, hass, entry_id, slug, catalog_params, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._slug = slug
        self._params = catalog_params
        uid = f"electricity_{slug}_export_price"
        self._attr_unique_id = uid
        self.entity_id = f"sensor.{uid}"
        self._attr_name = NAMES.get(
            ("electricity_supplier_export_price", language),
            NAMES[("electricity_supplier_export_price", LANG_EN)],
        )

    def _get_store(self):
        return self.hass.data.get(DOMAIN, {}).get("nordpool_store")

    @callback
    def _update(self) -> None:
        store = self._get_store()
        if store is None or store.monthly_average_spp is None:
            self._attr_native_value = None
            self._attr_available = False
            self.async_write_ha_state()
            return

        epex_spp = store.monthly_average_spp
        multiplier = self._params["epex_multiplier"]
        offset = self._params["epex_offset_cEur_kwh"]
        result = epex_spp * multiplier + offset
        self._attr_native_value = round(result, 5)
        self._attr_available = True
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub_listeners.append(
            async_dispatcher_connect(self.hass, SIGNAL_NORDPOOL_UPDATE, self._update)
        )
        self._update()


class ElectricitySupplierExportPriceEurSensor(KrowiSensor):
    """Supplier-specific electricity export price in EUR/kWh (BTW-vrij)."""

    _attr_icon = "mdi:currency-eur"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "EUR/kWh"

    def __init__(self, hass, entry_id, slug, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._slug = slug
        self._source_uid = f"electricity_{slug}_export_price"
        uid = f"electricity_{slug}_export_price_eur"
        self._attr_unique_id = uid
        self.entity_id = f"sensor.{uid}"
        self._attr_name = NAMES.get(
            ("electricity_supplier_export_price_eur", language),
            NAMES[("electricity_supplier_export_price_eur", LANG_EN)],
        )

    def _subscribe_listeners(self) -> None:
        source_id = _resolve_entity_id(self.hass, "sensor", self._source_uid)
        if source_id:
            self._track([source_id], self._handle_state_change)

    @callback
    def _handle_state_change(self, event) -> None:
        self._update()

    def _update(self) -> None:
        source_id = _resolve_entity_id(self.hass, "sensor", self._source_uid)
        val = safe_float_state(self.hass, source_id) if source_id else None
        if val is None:
            self._attr_native_value = None
            self._attr_available = False
        else:
            self._attr_native_value = round(val / 100, 7)
            self._attr_available = True
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._update()


# ---------------------------------------------------------------------------
# Platform setup
# ---------------------------------------------------------------------------

async def async_setup(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up electricity supplier sensor entities for this config entry."""
    effective = {**entry.data, **entry.options}
    slug = entry.data[CONF_SUPPLIER_SLUG]
    label = effective.get(CONF_SUPPLIER_LABEL, slug)
    catalog_entry = ELECTRICITY_SUPPLIER_CATALOG.get(slug, {})
    import_params = catalog_entry.get("import", {})
    export_params = catalog_entry.get("export", {})
    entry_id = entry.entry_id
    language = get_language(hass)
    device_info = DeviceInfo(
        identifiers={(DOMAIN, f"{entry_id}_{slug}")},
        name=label,
    )
    entities = [
        ElectricitySupplierImportPriceSensor(hass, entry_id, slug, import_params, device_info, language),
        ElectricitySupplierImportPriceEurSensor(hass, entry_id, slug, device_info, language),
        ElectricitySupplierExportPriceSensor(hass, entry_id, slug, export_params, device_info, language),
        ElectricitySupplierExportPriceEurSensor(hass, entry_id, slug, device_info, language),
    ]
    async_add_entities(entities)
