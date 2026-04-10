"""Sensor entities for Krowi Energy Management."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass # type: ignore
from homeassistant.config_entries import ConfigEntry # type: ignore
from homeassistant.const import STATE_UNAVAILABLE # type: ignore
from homeassistant.core import HomeAssistant, callback # type: ignore
from homeassistant.helpers import entity_registry as er # type: ignore
from homeassistant.helpers.device_registry import DeviceInfo # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback # type: ignore
from homeassistant.helpers.event import ( # type: ignore
    TrackTemplate,
    async_track_state_change_event,
    async_track_template_result,
)
from homeassistant.helpers.template import Template # type: ignore

from .const import (
    CONF_CURRENT_PRICE_ENTITY,
    CONF_DOMAIN_TYPE,
    CONF_EXPORT_TEMPLATE,
    CONF_FX_RATE_ENTITY,
    CONF_UNIT,
    DOMAIN,
    DOMAIN_TYPE_ELECTRICITY,
    LANG_EN,
    NAMES,
    UNIT_ELECTRICITY,
    UID_ELECTRICITY_DISTRIBUTION_TRANSPORT,
    UID_ELECTRICITY_ENERGY_CONTRIBUTION,
    UID_ELECTRICITY_EXCISE_DUTY,
    UID_ELECTRICITY_GREEN_ENERGY,
    UID_ELECTRICITY_PRICE_EXPORT,
    UID_ELECTRICITY_PRICE_EXPORT_EUR,
    UID_ELECTRICITY_PRICE_IMPORT,
    UID_ELECTRICITY_PRICE_IMPORT_EUR,
    UID_ELECTRICITY_SURCHARGE_FORMULA,
    UID_ELECTRICITY_SURCHARGE_RATE,
    UID_ELECTRICITY_VAT,
    UID_GAS_DISTRIBUTION,
    UID_GAS_ENERGY_CONTRIBUTION,
    UID_GAS_EXCISE_DUTY,
    UID_GAS_PRICE,
    UID_GAS_PRICE_EUR,
    UID_GAS_SURCHARGE_FORMULA,
    UID_GAS_SURCHARGE_RATE,
    UID_GAS_TRANSPORT,
    UID_GAS_VAT,
)
from .utils import apply_fx, convert_unit, get_language, safe_float_state

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
    unit = UNIT_ELECTRICITY if domain_type == DOMAIN_TYPE_ELECTRICITY else effective[CONF_UNIT]
    entry_id = entry.entry_id
    language = get_language(hass)

    if domain_type == DOMAIN_TYPE_ELECTRICITY:
        device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_electricity")},
            name="Electricity",
        )
        current_price_entity = effective[CONF_CURRENT_PRICE_ENTITY]
        fx_rate_entity = effective.get(CONF_FX_RATE_ENTITY) or ""
        export_template_str = effective[CONF_EXPORT_TEMPLATE]

        entities = [
            ElectricitySurchargeSensor(hass, entry_id, unit, device_info, language),
            ElectricitySurchargeFormulaSensor(hass, entry_id, unit, device_info, language),
            ElectricityImportPriceSensor(
                hass, entry_id, unit, current_price_entity, fx_rate_entity, device_info, language
            ),
            ElectricityExportPriceSensor(
                hass, entry_id, unit, export_template_str, device_info, language
            ),
            ElectricityImportPriceEurSensor(hass, entry_id, device_info, language),
            ElectricityExportPriceEurSensor(hass, entry_id, device_info, language),
        ]
    else:
        device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_gas")},
            name="Gas",
        )
        current_price_entity = effective[CONF_CURRENT_PRICE_ENTITY]

        entities = [
            GasSurchargeSensor(hass, entry_id, unit, device_info, language),
            GasSurchargeFormulaSensor(hass, entry_id, unit, device_info, language),
            GasCurrentPriceSensor(hass, entry_id, unit, current_price_entity, device_info, language),
            GasCurrentPriceEurSensor(hass, entry_id, unit, device_info, language),
        ]

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
# Electricity surcharge sensors
# ---------------------------------------------------------------------------

class ElectricitySurchargeSensor(KrowiSensor):
    """Sum of the four electricity rate number entities."""

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
    """Electricity import price: (current_price_converted + surcharge) * (1 + vat/100)."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, entry_id, unit, current_price_entity, fx_rate_entity, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_ELECTRICITY_PRICE_IMPORT
        self.entity_id = f"sensor.{UID_ELECTRICITY_PRICE_IMPORT}"
        self._attr_name = NAMES.get((UID_ELECTRICITY_PRICE_IMPORT, language), NAMES[(UID_ELECTRICITY_PRICE_IMPORT, LANG_EN)])
        self._attr_native_unit_of_measurement = unit
        self._unit = unit
        self._current_price_entity = current_price_entity
        self._fx_rate_entity = fx_rate_entity or ""

    def _subscribe_listeners(self) -> None:
        watch = [self._current_price_entity]
        if self._fx_rate_entity:
            watch.append(self._fx_rate_entity)

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
        # Read current price with unit conversion
        price_state = self.hass.states.get(self._current_price_entity)
        if price_state is None or price_state.state in ("unavailable", "unknown"):
            _LOGGER.warning(
                "krowi_energy_management: current price entity '%s' unavailable",
                self._current_price_entity,
            )
            self._attr_native_value = None
            self._attr_available = False
            self.async_write_ha_state()
            return

        try:
            raw_price = float(price_state.state)
        except (ValueError, TypeError):
            self._attr_native_value = None
            self._attr_available = False
            self.async_write_ha_state()
            return

        source_unit = price_state.attributes.get("unit_of_measurement", "")
        converted = convert_unit(raw_price, source_unit, self._unit)
        if converted is None:
            self._attr_native_value = None
            self._attr_available = False
            self.async_write_ha_state()
            return

        # Apply FX
        converted = apply_fx(converted, self._fx_rate_entity, self.hass)
        if converted is None:
            self._attr_native_value = None
            self._attr_available = False
            self.async_write_ha_state()
            return

        # Surcharge
        surcharge_id = _resolve_entity_id(self.hass, "sensor", UID_ELECTRICITY_SURCHARGE_RATE)
        surcharge = safe_float_state(self.hass, surcharge_id) if surcharge_id else 0.0
        if surcharge is None:
            surcharge = 0.0

        # VAT
        vat_id = _resolve_entity_id(self.hass, "number", UID_ELECTRICITY_VAT)
        vat = safe_float_state(self.hass, vat_id) if vat_id else 0.0
        if vat is None:
            vat = 0.0

        result = (converted + surcharge) * (1 + vat / 100)
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
# Gas surcharge sensor
# ---------------------------------------------------------------------------

class GasSurchargeSensor(KrowiSensor):
    """Sum of the four gas rate number entities."""

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
                UID_GAS_DISTRIBUTION,
                UID_GAS_TRANSPORT,
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
            UID_GAS_DISTRIBUTION,
            UID_GAS_TRANSPORT,
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
                UID_GAS_DISTRIBUTION,
                UID_GAS_TRANSPORT,
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
            UID_GAS_DISTRIBUTION,
            UID_GAS_TRANSPORT,
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
    """Gas price: (current_price_converted + surcharge) * (1 + vat/100)."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, entry_id, unit, current_price_entity, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_GAS_PRICE
        self.entity_id = f"sensor.{UID_GAS_PRICE}"
        self._attr_name = NAMES.get((UID_GAS_PRICE, language), NAMES[(UID_GAS_PRICE, LANG_EN)])
        self._attr_native_unit_of_measurement = unit
        self._unit = unit
        self._current_price_entity = current_price_entity

    def _subscribe_listeners(self) -> None:
        watch = [self._current_price_entity]

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
        price_state = self.hass.states.get(self._current_price_entity)
        if price_state is None or price_state.state in ("unavailable", "unknown"):
            _LOGGER.warning(
                "krowi_energy_management: gas price entity '%s' unavailable",
                self._current_price_entity,
            )
            self._attr_native_value = None
            self._attr_available = False
            self.async_write_ha_state()
            return

        try:
            raw_price = float(price_state.state)
        except (ValueError, TypeError):
            self._attr_native_value = None
            self._attr_available = False
            self.async_write_ha_state()
            return

        source_unit = price_state.attributes.get("unit_of_measurement", "")
        converted = convert_unit(raw_price, source_unit, self._unit)
        if converted is None:
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

        result = (converted + surcharge) * (1 + vat / 100)
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
    """Gas current price in EUR/kWh, derived from gas_current_price via convert_unit."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "EUR/kWh"

    def __init__(self, hass, entry_id, gas_unit, device_info, language=LANG_EN):
        super().__init__(hass, entry_id, device_info)
        self._attr_unique_id = UID_GAS_PRICE_EUR
        self.entity_id = f"sensor.{UID_GAS_PRICE_EUR}"
        self._attr_name = NAMES.get((UID_GAS_PRICE_EUR, language), NAMES[(UID_GAS_PRICE_EUR, LANG_EN)])
        self._gas_unit = gas_unit

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
        if value is None:
            self._attr_native_value = None
            self.async_write_ha_state()
            return
        converted = convert_unit(value, self._gas_unit, "EUR/kWh")
        self._attr_native_value = round(converted, 5) if converted is not None else None
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._update()
