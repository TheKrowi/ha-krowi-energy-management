"""Gas-domain sensor entities for Krowi Energy Management."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass  # type: ignore
from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.core import HomeAssistant, callback  # type: ignore
from homeassistant.helpers.restore_state import RestoreEntity  # type: ignore
from homeassistant.helpers.device_registry import DeviceInfo  # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback  # type: ignore
from homeassistant.helpers.dispatcher import async_dispatcher_connect  # type: ignore

from .const import (
    CONF_GAS_METER_ENTITY,
    DEFAULT_GAS_METER_ENTITY,
    DOMAIN,
    GAS_UNIT,
    LANG_EN,
    NAMES,
    SIGNAL_GCV_UPDATE,
    SIGNAL_TTF_DAM_UPDATE,
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
from .sensor_base import KrowiSensor, _resolve_entity_id
from .utils import get_language, safe_float_state

_LOGGER = logging.getLogger(__name__)


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
# Platform setup
# ---------------------------------------------------------------------------

async def async_setup(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up gas sensor entities for this config entry."""
    effective = {**entry.data, **entry.options}
    entry_id = entry.entry_id
    language = get_language(hass)
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
    async_add_entities(entities)
