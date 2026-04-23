"""Sensor entities for Krowi Energy Management."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass  # type: ignore
from homeassistant.config_entries import ConfigEntry # type: ignore
from homeassistant.const import STATE_UNAVAILABLE # type: ignore
from homeassistant.core import HomeAssistant, callback # type: ignore
from homeassistant.helpers.restore_state import RestoreEntity  # type: ignore
from homeassistant.helpers import entity_registry as er # type: ignore
from homeassistant.helpers.device_registry import DeviceInfo # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback # type: ignore
from homeassistant.helpers.dispatcher import async_dispatcher_connect # type: ignore
from homeassistant.helpers.event import ( # type: ignore
    TrackTemplate,
    async_track_state_change_event,
    async_track_template_result,
)
from homeassistant.helpers.template import Template # type: ignore

from .const import (
    CONF_DOMAIN_TYPE,
    CONF_ELECTRICITY_EXPORT_T1_METER,
    CONF_ELECTRICITY_EXPORT_T1_PRICE,
    CONF_ELECTRICITY_EXPORT_T2_METER,
    CONF_ELECTRICITY_EXPORT_T2_PRICE,
    CONF_ELECTRICITY_IMPORT_T1_METER,
    CONF_ELECTRICITY_IMPORT_T1_PRICE,
    CONF_ELECTRICITY_IMPORT_T2_METER,
    CONF_ELECTRICITY_IMPORT_T2_PRICE,
    CONF_EXPORT_TEMPLATE,
    CONF_GAS_METER_ENTITY,
    CONF_SUPPLIER_LABEL,
    CONF_SUPPLIER_SLUG,
    DEFAULT_ELECTRICITY_EXPORT_T1_METER,
    DEFAULT_ELECTRICITY_EXPORT_T1_PRICE,
    DEFAULT_ELECTRICITY_EXPORT_T2_METER,
    DEFAULT_ELECTRICITY_EXPORT_T2_PRICE,
    DEFAULT_ELECTRICITY_IMPORT_T1_METER,
    DEFAULT_ELECTRICITY_IMPORT_T1_PRICE,
    DEFAULT_ELECTRICITY_IMPORT_T2_METER,
    DEFAULT_ELECTRICITY_IMPORT_T2_PRICE,
    DEFAULT_GAS_METER_ENTITY,
    DOMAIN,
    DOMAIN_TYPE_ELECTRICITY,
    DOMAIN_TYPE_ELECTRICITY_SUPPLIER,
    DOMAIN_TYPE_GAS,
    ELECTRICITY_SUPPLIER_CATALOG,
    GAS_UNIT,
    LANG_EN,
    NAMES,
    SIGNAL_GCV_UPDATE,
    SIGNAL_NORDPOOL_UPDATE,
    SIGNAL_TTF_DAM_UPDATE,
    UNIT_ELECTRICITY,
    UID_ELECTRICITY_DISTRIBUTION_TRANSPORT,
    UID_ELECTRICITY_ENERGY_CONTRIBUTION,
    UID_ELECTRICITY_EXCISE_DUTY,
    UID_ELECTRICITY_EXPORT_REVENUE_T1,
    UID_ELECTRICITY_EXPORT_REVENUE_T2,
    UID_ELECTRICITY_GREEN_ENERGY,
    UID_ELECTRICITY_IMPORT_COST_T1,
    UID_ELECTRICITY_IMPORT_COST_T2,
    UID_ELECTRICITY_NET_COST,
    UID_ELECTRICITY_PRICE_EXPORT,
    UID_ELECTRICITY_PRICE_EXPORT_EUR,
    UID_ELECTRICITY_PRICE_IMPORT,
    UID_ELECTRICITY_PRICE_IMPORT_EUR,
    UID_ELECTRICITY_SPOT_AVERAGE_PRICE,
    UID_ELECTRICITY_SPOT_AVERAGE_PRICE_RLP,
    UID_ELECTRICITY_SPOT_AVERAGE_PRICE_SPP,
    UID_ELECTRICITY_SPOT_CURRENT_PRICE,
    UID_ELECTRICITY_SURCHARGE_FORMULA,
    UID_ELECTRICITY_SURCHARGE_RATE,
    UID_ELECTRICITY_TOTAL_EXPORT_REVENUE,
    UID_ELECTRICITY_TOTAL_IMPORT_COST,
    UID_ELECTRICITY_VAT,
    UID_GAS_CALORIFIC_VALUE,
    UID_GAS_CONSUMPTION_KWH,
    UID_GAS_TOTAL_COST,
    UID_GAS_DISTRIBUTION,
    UID_GAS_ENERGY_CONTRIBUTION,
    UID_GAS_EXCISE_DUTY,
    UID_GAS_PRICE,
    UID_GAS_PRICE_EUR,
    UID_GAS_PRICE_M3,
    UID_GAS_SPOT_AVERAGE_PRICE,
    UID_GAS_SPOT_TODAY_PRICE,
    UID_GAS_SURCHARGE_FORMULA,
    UID_GAS_SURCHARGE_RATE,
    UID_GAS_TRANSPORT,
    UID_GAS_VAT,
)
from .utils import get_language, safe_float_state

_LOGGER = logging.getLogger(__name__)


def _resolve_entity_id(hass: HomeAssistant, platform: str, unique_id: str) -> str | None:
    """Look up the current entity_id for a unique_id via the entity registry."""
    registry = er.async_get(hass)
    return registry.async_get_entity_id(platform, DOMAIN, unique_id)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities for this config entry."""
    effective = {**entry.data, **entry.options}
    domain_type = entry.data[CONF_DOMAIN_TYPE]
    unit = UNIT_ELECTRICITY
    entry_id = entry.entry_id
    language = get_language(hass)

    if domain_type == DOMAIN_TYPE_ELECTRICITY:
        device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_electricity")},
            name="Electricity",
        )
        export_template_str = effective[CONF_EXPORT_TEMPLATE]
        import_t1_meter = effective.get(CONF_ELECTRICITY_IMPORT_T1_METER, DEFAULT_ELECTRICITY_IMPORT_T1_METER) or DEFAULT_ELECTRICITY_IMPORT_T1_METER
        import_t2_meter = effective.get(CONF_ELECTRICITY_IMPORT_T2_METER, DEFAULT_ELECTRICITY_IMPORT_T2_METER) or DEFAULT_ELECTRICITY_IMPORT_T2_METER
        export_t1_meter = effective.get(CONF_ELECTRICITY_EXPORT_T1_METER, DEFAULT_ELECTRICITY_EXPORT_T1_METER) or DEFAULT_ELECTRICITY_EXPORT_T1_METER
        export_t2_meter = effective.get(CONF_ELECTRICITY_EXPORT_T2_METER, DEFAULT_ELECTRICITY_EXPORT_T2_METER) or DEFAULT_ELECTRICITY_EXPORT_T2_METER
        import_t1_price = effective.get(CONF_ELECTRICITY_IMPORT_T1_PRICE, DEFAULT_ELECTRICITY_IMPORT_T1_PRICE) or DEFAULT_ELECTRICITY_IMPORT_T1_PRICE
        import_t2_price = effective.get(CONF_ELECTRICITY_IMPORT_T2_PRICE, DEFAULT_ELECTRICITY_IMPORT_T2_PRICE) or DEFAULT_ELECTRICITY_IMPORT_T2_PRICE
        export_t1_price = effective.get(CONF_ELECTRICITY_EXPORT_T1_PRICE, DEFAULT_ELECTRICITY_EXPORT_T1_PRICE) or DEFAULT_ELECTRICITY_EXPORT_T1_PRICE
        export_t2_price = effective.get(CONF_ELECTRICITY_EXPORT_T2_PRICE, DEFAULT_ELECTRICITY_EXPORT_T2_PRICE) or DEFAULT_ELECTRICITY_EXPORT_T2_PRICE

        entities = [
            ElectricitySpotCurrentPriceSensor(hass, entry_id, device_info, language),
            ElectricitySpotAverageSensor(hass, entry_id, device_info, language),
            ElectricitySpotAveragePriceRLPSensor(hass, entry_id, device_info, language),
            ElectricitySpotAveragePriceSPPSensor(hass, entry_id, device_info, language),
            ElectricitySurchargeSensor(hass, entry_id, unit, device_info, language),
            ElectricitySurchargeFormulaSensor(hass, entry_id, unit, device_info, language),
            ElectricityImportPriceSensor(hass, entry_id, device_info, language),
            ElectricityExportPriceSensor(
                hass, entry_id, unit, export_template_str, device_info, language
            ),
            ElectricityImportPriceEurSensor(hass, entry_id, device_info, language),
            ElectricityExportPriceEurSensor(hass, entry_id, device_info, language),
            ElectricityImportCostT1Sensor(hass, entry_id, import_t1_meter, import_t1_price, device_info, language),
            ElectricityImportCostT2Sensor(hass, entry_id, import_t2_meter, import_t2_price, device_info, language),
            ElectricityExportRevenueT1Sensor(hass, entry_id, export_t1_meter, export_t1_price, device_info, language),
            ElectricityExportRevenueT2Sensor(hass, entry_id, export_t2_meter, export_t2_price, device_info, language),
            ElectricityTotalImportCostSensor(hass, entry_id, device_info, language),
            ElectricityTotalExportRevenueSensor(hass, entry_id, device_info, language),
            ElectricityNetCostSensor(hass, entry_id, device_info, language),
        ]
    elif domain_type == DOMAIN_TYPE_GAS:
        device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_gas")},
            name="Gas",
        )
        gas_meter_entity = effective.get(CONF_GAS_METER_ENTITY, DEFAULT_GAS_METER_ENTITY) or DEFAULT_GAS_METER_ENTITY

        entities = [
            GasSpotTodayPriceSensor(hass, entry_id, device_info, language),
            GasSpotAverageSensor(hass, entry_id, device_info, language),
            GasSurchargeSensor(hass, entry_id, GAS_UNIT, device_info, language),
            GasSurchargeFormulaSensor(hass, entry_id, GAS_UNIT, device_info, language),
            GasCurrentPriceSensor(hass, entry_id, device_info, language),
            GasCurrentPriceEurSensor(hass, entry_id, device_info, language),
            GasCalorificValueSensor(hass, entry_id, device_info, language),
            GasCurrentPriceM3Sensor(hass, entry_id, device_info, language),
            GasConsumptionKwhSensor(hass, entry_id, gas_meter_entity, device_info, language),
            GasTotalCostSensor(hass, entry_id, gas_meter_entity, device_info, language),
        ]
    elif domain_type == DOMAIN_TYPE_ELECTRICITY_SUPPLIER:
        slug = entry.data[CONF_SUPPLIER_SLUG]
        label = effective.get(CONF_SUPPLIER_LABEL, slug)
        catalog_entry = ELECTRICITY_SUPPLIER_CATALOG.get(slug, {})
        import_params = catalog_entry.get("import", {})
        export_params = catalog_entry.get("export", {})
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
    else:
        return

    async_add_entities(entities)


# ---------------------------------------------------------------------------
# Base sensor
# ---------------------------------------------------------------------------

class KrowiSensor(SensorEntity):
    """Base class for Krowi computed sensors."""

    _attr_should_poll = False
    _unsub_listeners: list = []

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        device_info: DeviceInfo,
    ) -> None:
        self.hass = hass
        self._entry_id = entry_id
        self._attr_device_info = device_info
        self._unsub_listeners = []

    async def async_added_to_hass(self) -> None:
        """Subscribe to state changes."""
        self._subscribe_listeners()

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe all listeners."""
        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()

    def _subscribe_listeners(self) -> None:
        """Override in subclasses to register state-change listeners."""

    def _track(self, entity_ids: list[str], handler) -> None:
        """Register a state-change listener, storing the unsubscribe callback."""
        self._unsub_listeners.append(
            async_track_state_change_event(self.hass, entity_ids, handler)
        )


# ---------------------------------------------------------------------------
# Electricity spot price sensors (Nord Pool BE, sourced from NordpoolBeStore)
# ---------------------------------------------------------------------------

class ElectricitySpotCurrentPriceSensor(KrowiSensor):
    """Current 15-min Nord Pool BE spot price in c€/kWh."""

    _attr_icon = "mdi:currency-eur"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UNIT_ELECTRICITY

    def __init__(self, hass, entry_id, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_ELECTRICITY_SPOT_CURRENT_PRICE
        self.entity_id = f"sensor.{UID_ELECTRICITY_SPOT_CURRENT_PRICE}"
        self._attr_name = NAMES.get(
            (UID_ELECTRICITY_SPOT_CURRENT_PRICE, language),
            NAMES[(UID_ELECTRICITY_SPOT_CURRENT_PRICE, LANG_EN)],
        )

    def _get_store(self):
        return self.hass.data.get(DOMAIN, {}).get("nordpool_store")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub_listeners.append(
            async_dispatcher_connect(self.hass, SIGNAL_NORDPOOL_UPDATE, self._on_update)
        )
        self._on_update()

    @callback
    def _on_update(self) -> None:
        store = self._get_store()
        if store is None or store.current_price is None:
            self._attr_native_value = None
            self._attr_available = False
        else:
            self._attr_native_value = store.current_price
            self._attr_available = True
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict:
        store = self._get_store()
        if store is None:
            return {}
        return {
            "today": store.today,
            "tomorrow": store.tomorrow,
            "tomorrow_valid": store.tomorrow_valid,
            "low_price": store.low_price,
            "price_percent_to_average": store.price_percent_to_average,
        }


class ElectricitySpotAverageSensor(KrowiSensor):
    """Rolling calendar-month average Nord Pool BE spot price in c€/kWh."""

    _attr_icon = "mdi:currency-eur"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UNIT_ELECTRICITY

    def __init__(self, hass, entry_id, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_ELECTRICITY_SPOT_AVERAGE_PRICE
        self.entity_id = f"sensor.{UID_ELECTRICITY_SPOT_AVERAGE_PRICE}"
        self._attr_name = NAMES.get(
            (UID_ELECTRICITY_SPOT_AVERAGE_PRICE, language),
            NAMES[(UID_ELECTRICITY_SPOT_AVERAGE_PRICE, LANG_EN)],
        )

    def _get_store(self):
        return self.hass.data.get(DOMAIN, {}).get("nordpool_store")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub_listeners.append(
            async_dispatcher_connect(self.hass, SIGNAL_NORDPOOL_UPDATE, self._on_update)
        )
        self._on_update()

    @callback
    def _on_update(self) -> None:
        store = self._get_store()
        if store is None or store.monthly_average is None:
            self._attr_native_value = None
            self._attr_available = False
        else:
            self._attr_native_value = store.monthly_average
            self._attr_available = True
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict:
        store = self._get_store()
        if store is None:
            return {"history": {}}
        return {
            "history": {
                d.isoformat(): v
                for d, v in store._daily_avg_buffer.items()
            },
        }


class ElectricitySpotAveragePriceRLPSensor(KrowiSensor):
    """Rolling calendar-month RLP-weighted average Nord Pool BE spot price in c€/kWh."""

    _attr_icon = "mdi:currency-eur"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UNIT_ELECTRICITY

    def __init__(self, hass, entry_id, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_ELECTRICITY_SPOT_AVERAGE_PRICE_RLP
        self.entity_id = f"sensor.{UID_ELECTRICITY_SPOT_AVERAGE_PRICE_RLP}"
        self._attr_name = NAMES.get(
            (UID_ELECTRICITY_SPOT_AVERAGE_PRICE_RLP, language),
            NAMES[(UID_ELECTRICITY_SPOT_AVERAGE_PRICE_RLP, LANG_EN)],
        )

    def _get_store(self):
        return self.hass.data.get(DOMAIN, {}).get("nordpool_store")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub_listeners.append(
            async_dispatcher_connect(self.hass, SIGNAL_NORDPOOL_UPDATE, self._on_update)
        )
        self._on_update()

    @callback
    def _on_update(self) -> None:
        store = self._get_store()
        if store is None or store.monthly_average_rlp is None:
            self._attr_native_value = None
            self._attr_available = False
        else:
            self._attr_native_value = store.monthly_average_rlp
            self._attr_available = True
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict:
        store = self._get_store()
        if store is None:
            return {"rlp_available": False}
        return {
            "rlp_available": store.rlp_fully_available(),
        }


class ElectricitySpotAveragePriceSPPSensor(KrowiSensor):
    """Rolling calendar-month SPP-weighted average Nord Pool BE spot price in c€/kWh."""

    _attr_icon = "mdi:currency-eur"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UNIT_ELECTRICITY

    def __init__(self, hass, entry_id, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_ELECTRICITY_SPOT_AVERAGE_PRICE_SPP
        self.entity_id = f"sensor.{UID_ELECTRICITY_SPOT_AVERAGE_PRICE_SPP}"
        self._attr_name = NAMES.get(
            (UID_ELECTRICITY_SPOT_AVERAGE_PRICE_SPP, language),
            NAMES[(UID_ELECTRICITY_SPOT_AVERAGE_PRICE_SPP, LANG_EN)],
        )

    def _get_store(self):
        return self.hass.data.get(DOMAIN, {}).get("nordpool_store")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub_listeners.append(
            async_dispatcher_connect(self.hass, SIGNAL_NORDPOOL_UPDATE, self._on_update)
        )
        self._on_update()

    @callback
    def _on_update(self) -> None:
        store = self._get_store()
        if store is None or store.monthly_average_spp is None:
            self._attr_native_value = None
            self._attr_available = False
        else:
            self._attr_native_value = store.monthly_average_spp
            self._attr_available = True
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict:
        store = self._get_store()
        if store is None:
            return {"spp_available": False}
        return {
            "spp_available": store.spp_fully_available(),
        }


# ---------------------------------------------------------------------------
# Electricity surcharge sensors
# ---------------------------------------------------------------------------

class ElectricitySurchargeSensor(KrowiSensor):
    """Sum of the four electricity rate number entities."""

    _attr_icon = "mdi:cash-lock"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, entry_id, unit, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_ELECTRICITY_SURCHARGE_RATE
        self.entity_id = f"sensor.{UID_ELECTRICITY_SURCHARGE_RATE}"
        self._attr_name = NAMES.get((UID_ELECTRICITY_SURCHARGE_RATE, language), NAMES[(UID_ELECTRICITY_SURCHARGE_RATE, LANG_EN)])
        self._attr_native_unit_of_measurement = unit
        self._attr_native_value = 0.0

    def _rate_entity_ids(self) -> list[str]:
        return [
            eid for uid in [
                UID_ELECTRICITY_GREEN_ENERGY,
                UID_ELECTRICITY_DISTRIBUTION_TRANSPORT,
                UID_ELECTRICITY_EXCISE_DUTY,
                UID_ELECTRICITY_ENERGY_CONTRIBUTION,
            ]
            if (eid := _resolve_entity_id(self.hass, "number", uid)) is not None
        ]

    def _subscribe_listeners(self) -> None:
        ids = self._rate_entity_ids()
        if ids:
            self._track(ids, self._handle_state_change)

    @callback
    def _handle_state_change(self, event) -> None:
        self._update()

    def _update(self) -> None:
        total = 0.0
        for uid in [
            UID_ELECTRICITY_GREEN_ENERGY,
            UID_ELECTRICITY_DISTRIBUTION_TRANSPORT,
            UID_ELECTRICITY_EXCISE_DUTY,
            UID_ELECTRICITY_ENERGY_CONTRIBUTION,
        ]:
            eid = _resolve_entity_id(self.hass, "number", uid)
            value = safe_float_state(self.hass, eid) if eid else None
            if value is None:
                value = 0.0
            total += value
        self._attr_native_value = round(total, 5)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._update()


class ElectricitySurchargeFormulaSensor(KrowiSensor):
    """Human-readable formula string for the electricity surcharge."""

    _attr_icon = "mdi:function-variant"
    # No unit, no state_class
    _attr_native_unit_of_measurement = None
    _attr_state_class = None

    def __init__(self, hass, entry_id, unit, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_ELECTRICITY_SURCHARGE_FORMULA
        self.entity_id = f"sensor.{UID_ELECTRICITY_SURCHARGE_FORMULA}"
        self._attr_name = NAMES.get((UID_ELECTRICITY_SURCHARGE_FORMULA, language), NAMES[(UID_ELECTRICITY_SURCHARGE_FORMULA, LANG_EN)])
        self._unit = unit
        self._attr_native_value = f"0.00000 + 0.00000 + 0.00000 + 0.00000 = 0.00000 {unit}"

    def _rate_entity_ids(self) -> list[str]:
        return [
            eid for uid in [
                UID_ELECTRICITY_GREEN_ENERGY,
                UID_ELECTRICITY_DISTRIBUTION_TRANSPORT,
                UID_ELECTRICITY_EXCISE_DUTY,
                UID_ELECTRICITY_ENERGY_CONTRIBUTION,
            ]
            if (eid := _resolve_entity_id(self.hass, "number", uid)) is not None
        ]

    def _subscribe_listeners(self) -> None:
        ids = self._rate_entity_ids()
        if ids:
            self._track(ids, self._handle_state_change)

    @callback
    def _handle_state_change(self, event) -> None:
        self._update()

    def _update(self) -> None:
        values = []
        for uid in [
            UID_ELECTRICITY_GREEN_ENERGY,
            UID_ELECTRICITY_DISTRIBUTION_TRANSPORT,
            UID_ELECTRICITY_EXCISE_DUTY,
            UID_ELECTRICITY_ENERGY_CONTRIBUTION,
        ]:
            eid = _resolve_entity_id(self.hass, "number", uid)
            v = safe_float_state(self.hass, eid) if eid else None
            values.append(0.0 if v is None else v)

        total = round(sum(values), 5)
        parts = " + ".join(f"{v:.5f}" for v in values)
        self._attr_native_value = f"{parts} = {total:.5f} {self._unit}"
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._update()


# ---------------------------------------------------------------------------
# Electricity import price sensor
# ---------------------------------------------------------------------------

class ElectricityImportPriceSensor(KrowiSensor):
    """Electricity import price: (spot_price + surcharge) * (1 + vat/100)."""

    _attr_icon = "mdi:currency-eur"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, entry_id, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_ELECTRICITY_PRICE_IMPORT
        self.entity_id = f"sensor.{UID_ELECTRICITY_PRICE_IMPORT}"
        self._attr_name = NAMES.get((UID_ELECTRICITY_PRICE_IMPORT, language), NAMES[(UID_ELECTRICITY_PRICE_IMPORT, LANG_EN)])
        self._attr_native_unit_of_measurement = UNIT_ELECTRICITY

    def _subscribe_listeners(self) -> None:
        watch = []
        spot_id = _resolve_entity_id(self.hass, "sensor", UID_ELECTRICITY_SPOT_CURRENT_PRICE)
        if spot_id:
            watch.append(spot_id)
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

    def _update(self) -> None:
        spot_id = _resolve_entity_id(self.hass, "sensor", UID_ELECTRICITY_SPOT_CURRENT_PRICE)
        spot_state = self.hass.states.get(spot_id) if spot_id else None
        if spot_state is None or spot_state.state in ("unavailable", "unknown"):
            self._attr_native_value = None
            self._attr_available = False
            self.async_write_ha_state()
            return

        try:
            spot_price = float(spot_state.state)
        except (ValueError, TypeError):
            self._attr_native_value = None
            self._attr_available = False
            self.async_write_ha_state()
            return

        surcharge_id = _resolve_entity_id(self.hass, "sensor", UID_ELECTRICITY_SURCHARGE_RATE)
        surcharge = safe_float_state(self.hass, surcharge_id) if surcharge_id else 0.0
        if surcharge is None:
            surcharge = 0.0

        vat_id = _resolve_entity_id(self.hass, "number", UID_ELECTRICITY_VAT)
        vat = safe_float_state(self.hass, vat_id) if vat_id else 0.0
        if vat is None:
            vat = 0.0

        result = (spot_price + surcharge) * (1 + vat / 100)
        self._attr_native_value = round(result, 5)
        self._attr_available = True
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._update()


# ---------------------------------------------------------------------------
# Electricity export price sensor (reactive Jinja2 template)
# ---------------------------------------------------------------------------

class ElectricityExportPriceSensor(KrowiSensor):
    """Electricity export price rendered from a user-supplied Jinja2 template."""

    _attr_icon = "mdi:currency-eur"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _unsub_template = None

    def __init__(self, hass, entry_id, unit, export_template_str, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_ELECTRICITY_PRICE_EXPORT
        self.entity_id = f"sensor.{UID_ELECTRICITY_PRICE_EXPORT}"
        self._attr_name = NAMES.get((UID_ELECTRICITY_PRICE_EXPORT, language), NAMES[(UID_ELECTRICITY_PRICE_EXPORT, LANG_EN)])
        self._attr_native_unit_of_measurement = unit
        self._template = Template(export_template_str, hass)

    def _subscribe_listeners(self) -> None:
        @callback
        def _result_callback(event, updates) -> None:
            result = updates.pop().result
            if isinstance(result, Exception):
                _LOGGER.error(
                    "krowi_energy_management: export price template error: %s", result
                )
                self._attr_native_value = None
                self._attr_available = False
            else:
                try:
                    self._attr_native_value = round(float(result), 5)
                    self._attr_available = True
                except (ValueError, TypeError):
                    _LOGGER.error(
                        "krowi_energy_management: export price template returned non-numeric value: %s",
                        result,
                    )
                    self._attr_native_value = None
                    self._attr_available = False
            self.async_write_ha_state()

        self._unsub_template = async_track_template_result(
            self.hass,
            [TrackTemplate(self._template, None)],
            _result_callback,
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._unsub_template is not None:
            self._unsub_template.async_refresh()

    async def async_will_remove_from_hass(self) -> None:
        await super().async_will_remove_from_hass()
        if self._unsub_template is not None:
            self._unsub_template.async_remove()
            self._unsub_template = None


# ---------------------------------------------------------------------------
# Electricity EUR bridge sensors (EUR/kWh for HA Energy Dashboard)
# ---------------------------------------------------------------------------

class ElectricityImportPriceEurSensor(KrowiSensor):
    """Electricity import price in EUR/kWh (import price ÷ 100)."""

    _attr_icon = "mdi:currency-eur"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "EUR/kWh"

    def __init__(self, hass, entry_id, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_ELECTRICITY_PRICE_IMPORT_EUR
        self.entity_id = f"sensor.{UID_ELECTRICITY_PRICE_IMPORT_EUR}"
        self._attr_name = NAMES.get((UID_ELECTRICITY_PRICE_IMPORT_EUR, language), NAMES[(UID_ELECTRICITY_PRICE_IMPORT_EUR, LANG_EN)])

    def _source_entity_id(self) -> str | None:
        return _resolve_entity_id(self.hass, "sensor", UID_ELECTRICITY_PRICE_IMPORT)

    def _subscribe_listeners(self) -> None:
        source_id = self._source_entity_id()
        if source_id:
            self._track([source_id], self._handle_state_change)

    @callback
    def _handle_state_change(self, event) -> None:
        self._update()

    def _update(self) -> None:
        source_id = self._source_entity_id()
        value = safe_float_state(self.hass, source_id) if source_id else None
        self._attr_native_value = round(value / 100, 5) if value is not None else None
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._update()


class ElectricityExportPriceEurSensor(KrowiSensor):
    """Electricity export price in EUR/kWh (export price ÷ 100)."""

    _attr_icon = "mdi:currency-eur"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "EUR/kWh"

    def __init__(self, hass, entry_id, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_ELECTRICITY_PRICE_EXPORT_EUR
        self.entity_id = f"sensor.{UID_ELECTRICITY_PRICE_EXPORT_EUR}"
        self._attr_name = NAMES.get((UID_ELECTRICITY_PRICE_EXPORT_EUR, language), NAMES[(UID_ELECTRICITY_PRICE_EXPORT_EUR, LANG_EN)])

    def _source_entity_id(self) -> str | None:
        return _resolve_entity_id(self.hass, "sensor", UID_ELECTRICITY_PRICE_EXPORT)

    def _subscribe_listeners(self) -> None:
        source_id = self._source_entity_id()
        if source_id:
            self._track([source_id], self._handle_state_change)

    @callback
    def _handle_state_change(self, event) -> None:
        self._update()

    def _update(self) -> None:
        source_id = self._source_entity_id()
        value = safe_float_state(self.hass, source_id) if source_id else None
        self._attr_native_value = round(value / 100, 5) if value is not None else None
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._update()


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
# Gas spot price sensors (TTF DAM, sourced from TtfDamStore)
# ---------------------------------------------------------------------------

class GasSpotTodayPriceSensor(KrowiSensor):
    """Latest daily TTF DAM price in c€/kWh."""

    _attr_icon = "mdi:currency-eur"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = GAS_UNIT
    _attr_device_class = None

    def __init__(self, hass, entry_id, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_GAS_SPOT_TODAY_PRICE
        self.entity_id = f"sensor.{UID_GAS_SPOT_TODAY_PRICE}"
        self._attr_name = NAMES.get(
            (UID_GAS_SPOT_TODAY_PRICE, language),
            NAMES[(UID_GAS_SPOT_TODAY_PRICE, LANG_EN)],
        )

    def _get_store(self):
        return self.hass.data.get(DOMAIN, {}).get("ttf_dam_store")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub_listeners.append(
            async_dispatcher_connect(self.hass, SIGNAL_TTF_DAM_UPDATE, self._on_update)
        )
        self._on_update()

    @callback
    def _on_update(self) -> None:
        store = self._get_store()
        if store is None or store.today_price is None:
            self._attr_native_value = None
            self._attr_available = False
        else:
            self._attr_native_value = store.today_price
            self._attr_available = True
        self.async_write_ha_state()


class GasSpotAverageSensor(KrowiSensor):
    """30-day average TTF DAM price in c€/kWh."""

    _attr_icon = "mdi:currency-eur"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = GAS_UNIT
    _attr_device_class = None

    def __init__(self, hass, entry_id, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_GAS_SPOT_AVERAGE_PRICE
        self.entity_id = f"sensor.{UID_GAS_SPOT_AVERAGE_PRICE}"
        self._attr_name = NAMES.get(
            (UID_GAS_SPOT_AVERAGE_PRICE, language),
            NAMES[(UID_GAS_SPOT_AVERAGE_PRICE, LANG_EN)],
        )

    def _get_store(self):
        return self.hass.data.get(DOMAIN, {}).get("ttf_dam_store")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub_listeners.append(
            async_dispatcher_connect(self.hass, SIGNAL_TTF_DAM_UPDATE, self._on_update)
        )
        self._on_update()

    @callback
    def _on_update(self) -> None:
        store = self._get_store()
        if store is None or store.average is None:
            self._attr_native_value = None
            self._attr_available = False
        else:
            self._attr_native_value = store.average
            self._attr_available = True
        self.async_write_ha_state()


# ---------------------------------------------------------------------------
# Gas surcharge sensor
# ---------------------------------------------------------------------------

class GasSurchargeSensor(KrowiSensor):
    """Sum of the four gas rate number entities."""

    _attr_icon = "mdi:cash-lock"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, entry_id, unit, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_GAS_SURCHARGE_RATE
        self.entity_id = f"sensor.{UID_GAS_SURCHARGE_RATE}"
        self._attr_name = NAMES.get((UID_GAS_SURCHARGE_RATE, language), NAMES[(UID_GAS_SURCHARGE_RATE, LANG_EN)])
        self._attr_native_unit_of_measurement = unit
        self._attr_native_value = 0.0

    def _rate_entity_ids(self) -> list[str]:
        return [
            eid for uid in [
                UID_GAS_TRANSPORT,
                UID_GAS_DISTRIBUTION,
                UID_GAS_EXCISE_DUTY,
                UID_GAS_ENERGY_CONTRIBUTION,
            ]
            if (eid := _resolve_entity_id(self.hass, "number", uid)) is not None
        ]

    def _subscribe_listeners(self) -> None:
        ids = self._rate_entity_ids()
        if ids:
            self._track(ids, self._handle_state_change)

    @callback
    def _handle_state_change(self, event) -> None:
        self._update()

    def _update(self) -> None:
        total = 0.0
        for uid in [
            UID_GAS_TRANSPORT,
            UID_GAS_DISTRIBUTION,
            UID_GAS_EXCISE_DUTY,
            UID_GAS_ENERGY_CONTRIBUTION,
        ]:
            eid = _resolve_entity_id(self.hass, "number", uid)
            value = safe_float_state(self.hass, eid) if eid else None
            total += 0.0 if value is None else value
        self._attr_native_value = round(total, 5)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._update()


# ---------------------------------------------------------------------------
# Gas surcharge formula sensor
# ---------------------------------------------------------------------------

class GasSurchargeFormulaSensor(KrowiSensor):
    """Human-readable formula string for the gas surcharge."""

    _attr_icon = "mdi:function-variant"
    _attr_native_unit_of_measurement = None
    _attr_state_class = None

    def __init__(self, hass, entry_id, unit, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_GAS_SURCHARGE_FORMULA
        self.entity_id = f"sensor.{UID_GAS_SURCHARGE_FORMULA}"
        self._attr_name = NAMES.get((UID_GAS_SURCHARGE_FORMULA, language), NAMES[(UID_GAS_SURCHARGE_FORMULA, LANG_EN)])
        self._unit = unit
        self._attr_native_value = f"0.00000 + 0.00000 + 0.00000 + 0.00000 = 0.00000 {unit}"

    def _rate_entity_ids(self) -> list[str]:
        return [
            eid for uid in [
                UID_GAS_TRANSPORT,
                UID_GAS_DISTRIBUTION,
                UID_GAS_EXCISE_DUTY,
                UID_GAS_ENERGY_CONTRIBUTION,
            ]
            if (eid := _resolve_entity_id(self.hass, "number", uid)) is not None
        ]

    def _subscribe_listeners(self) -> None:
        ids = self._rate_entity_ids()
        if ids:
            self._track(ids, self._handle_state_change)

    @callback
    def _handle_state_change(self, event) -> None:
        self._update()

    def _update(self) -> None:
        values = []
        for uid in [
            UID_GAS_TRANSPORT,
            UID_GAS_DISTRIBUTION,
            UID_GAS_EXCISE_DUTY,
            UID_GAS_ENERGY_CONTRIBUTION,
        ]:
            eid = _resolve_entity_id(self.hass, "number", uid)
            v = safe_float_state(self.hass, eid) if eid else None
            values.append(0.0 if v is None else v)

        total = round(sum(values), 5)
        parts = " + ".join(f"{v:.5f}" for v in values)
        self._attr_native_value = f"{parts} = {total:.5f} {self._unit}"
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._update()


# ---------------------------------------------------------------------------
# Gas current price sensor
# ---------------------------------------------------------------------------

class GasCurrentPriceSensor(KrowiSensor):
    """Gas price: (spot_price + surcharge) * (1 + vat/100), always in c€/kWh."""

    _attr_icon = "mdi:currency-eur"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = GAS_UNIT

    def __init__(self, hass, entry_id, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_GAS_PRICE
        self.entity_id = f"sensor.{UID_GAS_PRICE}"
        self._attr_name = NAMES.get((UID_GAS_PRICE, language), NAMES[(UID_GAS_PRICE, LANG_EN)])

    def _subscribe_listeners(self) -> None:
        watch = []

        spot_id = _resolve_entity_id(self.hass, "sensor", UID_GAS_SPOT_AVERAGE_PRICE)
        if spot_id:
            watch.append(spot_id)

        surcharge_id = _resolve_entity_id(self.hass, "sensor", UID_GAS_SURCHARGE_RATE)
        if surcharge_id:
            watch.append(surcharge_id)

        vat_id = _resolve_entity_id(self.hass, "number", UID_GAS_VAT)
        if vat_id:
            watch.append(vat_id)

        if watch:
            self._track(watch, self._handle_state_change)

    @callback
    def _handle_state_change(self, event) -> None:
        self._update()

    def _update(self) -> None:
        spot_id = _resolve_entity_id(self.hass, "sensor", UID_GAS_SPOT_AVERAGE_PRICE)
        spot_state = self.hass.states.get(spot_id) if spot_id else None
        if spot_state is None or spot_state.state in ("unavailable", "unknown"):
            self._attr_native_value = None
            self._attr_available = False
            self.async_write_ha_state()
            return

        try:
            spot_price = float(spot_state.state)
        except (ValueError, TypeError):
            self._attr_native_value = None
            self._attr_available = False
            self.async_write_ha_state()
            return

        surcharge_id = _resolve_entity_id(self.hass, "sensor", UID_GAS_SURCHARGE_RATE)
        surcharge = safe_float_state(self.hass, surcharge_id) if surcharge_id else 0.0
        if surcharge is None:
            surcharge = 0.0

        vat_id = _resolve_entity_id(self.hass, "number", UID_GAS_VAT)
        vat = safe_float_state(self.hass, vat_id) if vat_id else 0.0
        if vat is None:
            vat = 0.0

        result = (spot_price + surcharge) * (1 + vat / 100)
        self._attr_native_value = round(result, 5)
        self._attr_available = True
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._update()


# ---------------------------------------------------------------------------
# Gas current price EUR/kWh bridge sensor
# ---------------------------------------------------------------------------

class GasCurrentPriceEurSensor(KrowiSensor):
    """Gas current price in EUR/kWh (gas_current_price ÷ 100, always c€/kWh source)."""

    _attr_icon = "mdi:currency-eur"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "EUR/kWh"

    def __init__(self, hass, entry_id, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_GAS_PRICE_EUR
        self.entity_id = f"sensor.{UID_GAS_PRICE_EUR}"
        self._attr_name = NAMES.get((UID_GAS_PRICE_EUR, language), NAMES[(UID_GAS_PRICE_EUR, LANG_EN)])

    def _source_entity_id(self) -> str | None:
        return _resolve_entity_id(self.hass, "sensor", UID_GAS_PRICE)

    def _subscribe_listeners(self) -> None:
        source_id = self._source_entity_id()
        if source_id:
            self._track([source_id], self._handle_state_change)

    @callback
    def _handle_state_change(self, event) -> None:
        self._update()

    def _update(self) -> None:
        source_id = self._source_entity_id()
        value = safe_float_state(self.hass, source_id) if source_id else None
        self._attr_native_value = round(value / 100, 5) if value is not None else None
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._update()


# ---------------------------------------------------------------------------
# Gas calorific value sensor (GcvStore)
# ---------------------------------------------------------------------------

class GasCalorificValueSensor(KrowiSensor):
    """Monthly GCV for the configured GOS zone in kWh/m³, sourced from GcvStore."""

    _attr_icon = "mdi:fire"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "kWh/m³"
    _attr_device_class = None

    def __init__(self, hass, entry_id, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_GAS_CALORIFIC_VALUE
        self.entity_id = f"sensor.{UID_GAS_CALORIFIC_VALUE}"
        self._attr_name = NAMES.get(
            (UID_GAS_CALORIFIC_VALUE, language),
            NAMES[(UID_GAS_CALORIFIC_VALUE, LANG_EN)],
        )

    def _get_store(self):
        return self.hass.data.get(DOMAIN, {}).get("gcv_store")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub_listeners.append(
            async_dispatcher_connect(self.hass, SIGNAL_GCV_UPDATE, self._on_update)
        )
        self._on_update()

    @callback
    def _on_update(self) -> None:
        store = self._get_store()
        if store is None or store.gcv is None:
            self._attr_native_value = None
            self._attr_available = False
        else:
            self._attr_native_value = store.gcv
            self._attr_available = True
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict:
        store = self._get_store()
        if store is None:
            return {"history": {}, "data_is_fresh": False}
        return {
            "history": store.history,
            "data_is_fresh": store.data_is_fresh,
        }


# ---------------------------------------------------------------------------
# Gas current price €/m³ sensor
# ---------------------------------------------------------------------------

class GasCurrentPriceM3Sensor(KrowiSensor):
    """Gas price in €/m³ = gas_current_price_eur × calorific_value."""

    _attr_icon = "mdi:currency-eur"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "€/m³"
    _attr_device_class = None

    def __init__(self, hass, entry_id, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_GAS_PRICE_M3
        self.entity_id = f"sensor.{UID_GAS_PRICE_M3}"
        self._attr_name = NAMES.get(
            (UID_GAS_PRICE_M3, language),
            NAMES[(UID_GAS_PRICE_M3, LANG_EN)],
        )

    def _get_store(self):
        return self.hass.data.get(DOMAIN, {}).get("gcv_store")

    def _source_entity_id(self) -> str | None:
        return _resolve_entity_id(self.hass, "sensor", UID_GAS_PRICE_EUR)

    def _subscribe_listeners(self) -> None:
        source_id = self._source_entity_id()
        if source_id:
            self._track([source_id], self._handle_state_change)

    @callback
    def _handle_state_change(self, event) -> None:
        self._update()

    def _update(self) -> None:
        store = self._get_store()
        if store is None or store.gcv is None:
            self._attr_native_value = None
            self._attr_available = False
            self.async_write_ha_state()
            return

        source_id = self._source_entity_id()
        eur_kwh = safe_float_state(self.hass, source_id) if source_id else None
        if eur_kwh is None:
            self._attr_native_value = None
            self._attr_available = False
        else:
            self._attr_native_value = round(eur_kwh * store.gcv, 5)
            self._attr_available = True
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._update()


# ---------------------------------------------------------------------------
# Gas consumption kWh sensor
# ---------------------------------------------------------------------------

class GasConsumptionKwhSensor(KrowiSensor):
    """Gas consumption in kWh = gas_meter_m³ × calorific_value."""

    _attr_icon = "mdi:meter-gas"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "kWh"
    _attr_device_class = SensorDeviceClass.ENERGY

    def __init__(self, hass, entry_id, gas_meter_entity: str, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._gas_meter_entity = gas_meter_entity
        self._attr_unique_id = UID_GAS_CONSUMPTION_KWH
        self.entity_id = f"sensor.{UID_GAS_CONSUMPTION_KWH}"
        self._attr_name = NAMES.get(
            (UID_GAS_CONSUMPTION_KWH, language),
            NAMES[(UID_GAS_CONSUMPTION_KWH, LANG_EN)],
        )

    def _get_store(self):
        return self.hass.data.get(DOMAIN, {}).get("gcv_store")

    def _subscribe_listeners(self) -> None:
        if self._gas_meter_entity:
            self._track([self._gas_meter_entity], self._handle_state_change)

    @callback
    def _handle_state_change(self, event) -> None:
        self._update()

    def _update(self) -> None:
        if not self._gas_meter_entity:
            self._attr_native_value = None
            self._attr_available = False
            self.async_write_ha_state()
            return

        store = self._get_store()
        if store is None or store.gcv is None:
            self._attr_native_value = None
            self._attr_available = False
            self.async_write_ha_state()
            return

        meter_state = self.hass.states.get(self._gas_meter_entity)
        if meter_state is None or meter_state.state in ("unavailable", "unknown"):
            self._attr_native_value = None
            self._attr_available = False
            self.async_write_ha_state()
            return

        try:
            m3 = float(meter_state.state)
        except (ValueError, TypeError):
            self._attr_native_value = None
            self._attr_available = False
            self.async_write_ha_state()
            return

        self._attr_native_value = round(m3 * store.gcv, 3)
        self._attr_available = True
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._update()


# ---------------------------------------------------------------------------
# Gas total cost sensor (accumulated EUR via RestoreEntity)
# ---------------------------------------------------------------------------

class GasTotalCostSensor(KrowiSensor, RestoreEntity):
    """Accumulated gas cost in EUR = Σ(Δm³ × GCV × price_EUR_per_kWh)."""

    _attr_icon = "mdi:invoice-text"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR"

    def __init__(self, hass, entry_id, gas_meter_entity: str, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._gas_meter_entity = gas_meter_entity
        self._attr_unique_id = UID_GAS_TOTAL_COST
        self.entity_id = f"sensor.{UID_GAS_TOTAL_COST}"
        self._attr_name = NAMES.get(
            (UID_GAS_TOTAL_COST, language),
            NAMES[(UID_GAS_TOTAL_COST, LANG_EN)],
        )
        self._last_m3: float | None = None
        self._last_known_price: float | None = None

    def _get_store(self):
        return self.hass.data.get(DOMAIN, {}).get("gcv_store")

    def _get_price_eur(self) -> float | None:
        price_id = _resolve_entity_id(self.hass, "sensor", UID_GAS_PRICE_EUR)
        return safe_float_state(self.hass, price_id) if price_id else None

    def _subscribe_listeners(self) -> None:
        if self._gas_meter_entity:
            self._track([self._gas_meter_entity], self._handle_state_change)

    @callback
    def _handle_state_change(self, event) -> None:
        self._update()

    def _update(self) -> None:
        if not self._gas_meter_entity:
            return

        # Read current meter state — skip tick if unavailable
        meter_state = self.hass.states.get(self._gas_meter_entity)
        if meter_state is None or meter_state.state in ("unavailable", "unknown"):
            return

        try:
            new_m3 = float(meter_state.state)
        except (ValueError, TypeError):
            return

        # Anchor on first reading
        if self._last_m3 is None:
            self._last_m3 = new_m3
            return

        delta_m3 = new_m3 - self._last_m3

        # Negative delta = meter replaced — re-anchor without adding cost
        if delta_m3 < 0:
            self._last_m3 = new_m3
            return

        # No consumption — nothing to do
        if delta_m3 == 0:
            return

        # GCV required — skip tick if unavailable
        store = self._get_store()
        if store is None or store.gcv is None:
            return

        # Price: use current or fall back to last known; skip if neither available
        price = self._get_price_eur()
        if price is not None:
            self._last_known_price = price
        elif self._last_known_price is not None:
            price = self._last_known_price
        else:
            return

        current_total = self._attr_native_value or 0.0
        increment = delta_m3 * store.gcv * price
        self._attr_native_value = round(current_total + increment, 5)
        self._attr_available = True
        self._last_m3 = new_m3
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        # Restore accumulated total from prior state
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in ("unavailable", "unknown", "None", None):
            try:
                self._attr_native_value = round(float(last_state.state), 5)
                self._attr_available = True
            except (ValueError, TypeError):
                self._attr_native_value = 0.0
        else:
            self._attr_native_value = 0.0

        # Anchor _last_m3 to current meter reading (don't cost the restart gap)
        if self._gas_meter_entity:
            meter_state = self.hass.states.get(self._gas_meter_entity)
            if meter_state is not None and meter_state.state not in ("unavailable", "unknown"):
                try:
                    self._last_m3 = float(meter_state.state)
                except (ValueError, TypeError):
                    pass

        await super().async_added_to_hass()


# ---------------------------------------------------------------------------
# Electricity per-tariff cost/revenue accumulator sensors
# ---------------------------------------------------------------------------

class _ElectricityTariffCostSensor(KrowiSensor, RestoreEntity):
    """Base class for per-tariff electricity cost/revenue accumulator sensors."""

    _attr_icon = "mdi:invoice-text-minus"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR"

    def __init__(
        self,
        hass,
        entry_id: str,
        meter_entity: str,
        price_entity: str,
        uid: str,
        device_info,
        language=LANG_EN,
    ):
        super().__init__(hass, entry_id, device_info)
        self._meter_entity = meter_entity or ""
        self._price_entity = price_entity or ""
        self._attr_unique_id = uid
        self.entity_id = f"sensor.{uid}"
        self._attr_name = NAMES.get((uid, language), NAMES[(uid, LANG_EN)])
        self._last_kwh: float | None = None
        self._last_known_price: float | None = None

    def _get_price(self) -> float | None:
        return safe_float_state(self.hass, self._price_entity) if self._price_entity else None

    def _subscribe_listeners(self) -> None:
        if self._meter_entity:
            self._track([self._meter_entity], self._handle_state_change)

    @callback
    def _handle_state_change(self, event) -> None:
        self._update()

    def _update(self) -> None:
        if not self._meter_entity:
            self._attr_available = False
            self.async_write_ha_state()
            return

        meter_state = self.hass.states.get(self._meter_entity)
        if meter_state is None or meter_state.state in ("unavailable", "unknown"):
            return

        try:
            new_kwh = float(meter_state.state)
        except (ValueError, TypeError):
            return

        # Anchor on first reading
        if self._last_kwh is None:
            self._last_kwh = new_kwh
            return

        delta_kwh = new_kwh - self._last_kwh

        # Negative delta = meter replaced — re-anchor without adding cost
        if delta_kwh < 0:
            self._last_kwh = new_kwh
            return

        if delta_kwh == 0:
            return

        # Price: use current or fall back to last known; skip if neither available
        price = self._get_price()
        if price is not None:
            self._last_known_price = price
        elif self._last_known_price is not None:
            price = self._last_known_price
        else:
            return

        current_total = self._attr_native_value or 0.0
        self._attr_native_value = round(current_total + delta_kwh * price, 5)
        self._attr_available = True
        self._last_kwh = new_kwh
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in ("unavailable", "unknown", "None", None):
            try:
                self._attr_native_value = round(float(last_state.state), 5)
                self._attr_available = True
            except (ValueError, TypeError):
                self._attr_native_value = 0.0
        else:
            self._attr_native_value = 0.0

        # Anchor _last_kwh to current meter reading (don't cost the restart gap)
        if self._meter_entity:
            meter_state = self.hass.states.get(self._meter_entity)
            if meter_state is not None and meter_state.state not in ("unavailable", "unknown"):
                try:
                    self._last_kwh = float(meter_state.state)
                except (ValueError, TypeError):
                    pass

        await super().async_added_to_hass()


class ElectricityImportCostT1Sensor(_ElectricityTariffCostSensor):
    """Accumulated import cost for tariff 1."""

    def __init__(self, hass, entry_id, meter_entity, price_entity, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, meter_entity, price_entity, UID_ELECTRICITY_IMPORT_COST_T1, device_info, language)


class ElectricityImportCostT2Sensor(_ElectricityTariffCostSensor):
    """Accumulated import cost for tariff 2."""

    def __init__(self, hass, entry_id, meter_entity, price_entity, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, meter_entity, price_entity, UID_ELECTRICITY_IMPORT_COST_T2, device_info, language)


class ElectricityExportRevenueT1Sensor(_ElectricityTariffCostSensor):
    """Accumulated export revenue for tariff 1."""

    _attr_icon = "mdi:invoice-text-plus"

    def __init__(self, hass, entry_id, meter_entity, price_entity, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, meter_entity, price_entity, UID_ELECTRICITY_EXPORT_REVENUE_T1, device_info, language)


class ElectricityExportRevenueT2Sensor(_ElectricityTariffCostSensor):
    """Accumulated export revenue for tariff 2."""

    _attr_icon = "mdi:invoice-text-plus"

    def __init__(self, hass, entry_id, meter_entity, price_entity, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, meter_entity, price_entity, UID_ELECTRICITY_EXPORT_REVENUE_T2, device_info, language)


# ---------------------------------------------------------------------------
# Electricity derived aggregate sensors
# ---------------------------------------------------------------------------

class ElectricityTotalImportCostSensor(KrowiSensor):
    """Total import cost = T1 + T2 (derived, no own accumulator)."""

    _attr_icon = "mdi:invoice-text-minus"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR"

    def __init__(self, hass, entry_id, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_ELECTRICITY_TOTAL_IMPORT_COST
        self.entity_id = f"sensor.{UID_ELECTRICITY_TOTAL_IMPORT_COST}"
        self._attr_name = NAMES.get(
            (UID_ELECTRICITY_TOTAL_IMPORT_COST, language),
            NAMES[(UID_ELECTRICITY_TOTAL_IMPORT_COST, LANG_EN)],
        )

    def _subscribe_listeners(self) -> None:
        t1_id = _resolve_entity_id(self.hass, "sensor", UID_ELECTRICITY_IMPORT_COST_T1)
        t2_id = _resolve_entity_id(self.hass, "sensor", UID_ELECTRICITY_IMPORT_COST_T2)
        ids = [i for i in [t1_id, t2_id] if i]
        if ids:
            self._track(ids, self._handle_state_change)

    @callback
    def _handle_state_change(self, event) -> None:
        self._update()

    def _update(self) -> None:
        t1_id = _resolve_entity_id(self.hass, "sensor", UID_ELECTRICITY_IMPORT_COST_T1)
        t2_id = _resolve_entity_id(self.hass, "sensor", UID_ELECTRICITY_IMPORT_COST_T2)
        t1 = safe_float_state(self.hass, t1_id) if t1_id else None
        t2 = safe_float_state(self.hass, t2_id) if t2_id else None
        if t1 is None and t2 is None:
            self._attr_native_value = None
            self._attr_available = False
        else:
            self._attr_native_value = round((t1 or 0.0) + (t2 or 0.0), 5)
            self._attr_available = True
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._update()


class ElectricityTotalExportRevenueSensor(KrowiSensor):
    """Total export revenue = T1 + T2 (derived, no own accumulator)."""

    _attr_icon = "mdi:invoice-text-plus"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR"

    def __init__(self, hass, entry_id, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_ELECTRICITY_TOTAL_EXPORT_REVENUE
        self.entity_id = f"sensor.{UID_ELECTRICITY_TOTAL_EXPORT_REVENUE}"
        self._attr_name = NAMES.get(
            (UID_ELECTRICITY_TOTAL_EXPORT_REVENUE, language),
            NAMES[(UID_ELECTRICITY_TOTAL_EXPORT_REVENUE, LANG_EN)],
        )

    def _subscribe_listeners(self) -> None:
        t1_id = _resolve_entity_id(self.hass, "sensor", UID_ELECTRICITY_EXPORT_REVENUE_T1)
        t2_id = _resolve_entity_id(self.hass, "sensor", UID_ELECTRICITY_EXPORT_REVENUE_T2)
        ids = [i for i in [t1_id, t2_id] if i]
        if ids:
            self._track(ids, self._handle_state_change)

    @callback
    def _handle_state_change(self, event) -> None:
        self._update()

    def _update(self) -> None:
        t1_id = _resolve_entity_id(self.hass, "sensor", UID_ELECTRICITY_EXPORT_REVENUE_T1)
        t2_id = _resolve_entity_id(self.hass, "sensor", UID_ELECTRICITY_EXPORT_REVENUE_T2)
        t1 = safe_float_state(self.hass, t1_id) if t1_id else None
        t2 = safe_float_state(self.hass, t2_id) if t2_id else None
        if t1 is None and t2 is None:
            self._attr_native_value = None
            self._attr_available = False
        else:
            self._attr_native_value = round((t1 or 0.0) + (t2 or 0.0), 5)
            self._attr_available = True
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._update()


class ElectricityNetCostSensor(KrowiSensor):
    """Net electricity cost = total import − total export (can go negative)."""

    _attr_icon = "mdi:invoice-text"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR"

    def __init__(self, hass, entry_id, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_ELECTRICITY_NET_COST
        self.entity_id = f"sensor.{UID_ELECTRICITY_NET_COST}"
        self._attr_name = NAMES.get(
            (UID_ELECTRICITY_NET_COST, language),
            NAMES[(UID_ELECTRICITY_NET_COST, LANG_EN)],
        )

    def _subscribe_listeners(self) -> None:
        import_id = _resolve_entity_id(self.hass, "sensor", UID_ELECTRICITY_TOTAL_IMPORT_COST)
        export_id = _resolve_entity_id(self.hass, "sensor", UID_ELECTRICITY_TOTAL_EXPORT_REVENUE)
        ids = [i for i in [import_id, export_id] if i]
        if ids:
            self._track(ids, self._handle_state_change)

    @callback
    def _handle_state_change(self, event) -> None:
        self._update()

    def _update(self) -> None:
        import_id = _resolve_entity_id(self.hass, "sensor", UID_ELECTRICITY_TOTAL_IMPORT_COST)
        export_id = _resolve_entity_id(self.hass, "sensor", UID_ELECTRICITY_TOTAL_EXPORT_REVENUE)
        total_import = safe_float_state(self.hass, import_id) if import_id else None
        total_export = safe_float_state(self.hass, export_id) if export_id else None
        if total_import is None or total_export is None:
            self._attr_native_value = None
            self._attr_available = False
        else:
            self._attr_native_value = round(total_import - total_export, 5)
            self._attr_available = True
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._update()
