"""Battery target-power sensor entities for Krowi Energy Management.

Two sensors are exposed per battery config entry:
  - battery_target_charge_power   = max(0, round(pid + charge_offset))
  - battery_target_discharge_power = abs(min(0, round(pid + discharge_offset)))

They are reactive: they subscribe to the PID output sensor and the two internal
offset number entities, recomputing whenever any of those change.
"""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass  # type: ignore
from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.core import HomeAssistant, callback  # type: ignore
from homeassistant.helpers import entity_registry as er  # type: ignore
from homeassistant.helpers.device_registry import DeviceInfo  # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback  # type: ignore
from homeassistant.helpers.event import async_track_state_change_event  # type: ignore

from .const import (
    CONF_BATTERY_PID_OUTPUT_SENSOR,
    DOMAIN,
    UID_BATTERY_CHARGE_OFFSET,
    UID_BATTERY_DISCHARGE_OFFSET,
    UID_BATTERY_TARGET_CHARGE_POWER,
    UID_BATTERY_TARGET_DISCHARGE_POWER,
)


def _state_float(hass: HomeAssistant, entity_id: str | None, default: float = 0.0) -> float:
    if not entity_id:
        return default
    state = hass.states.get(entity_id)
    if state is None:
        return default
    try:
        return float(state.state)
    except (ValueError, TypeError):
        return default


async def async_setup(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up battery target power sensors."""
    pid_entity_id: str = entry.data.get(
        CONF_BATTERY_PID_OUTPUT_SENSOR
    ) or entry.options.get(CONF_BATTERY_PID_OUTPUT_SENSOR, "")

    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
    )
    async_add_entities(
        [
            BatteryTargetChargePowerSensor(entry.entry_id, pid_entity_id, device_info),
            BatteryTargetDischargePowerSensor(entry.entry_id, pid_entity_id, device_info),
        ]
    )


class _BatteryTargetPowerBase(SensorEntity):
    """Shared base for the two battery target power sensors."""

    _attr_should_poll = False
    _attr_native_unit_of_measurement = "W"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_value: float = 0.0

    def __init__(
        self,
        entry_id: str,
        pid_entity_id: str,
        device_info: DeviceInfo,
    ) -> None:
        self._entry_id = entry_id
        self._pid_entity_id = pid_entity_id
        self._attr_device_info = device_info
        self._unsubs: list = []

    async def async_added_to_hass(self) -> None:
        registry = er.async_get(self.hass)
        offset_id = self._resolve_offset_id(registry)
        entities = [e for e in [self._pid_entity_id, offset_id] if e]
        if entities:
            self._unsubs.append(
                async_track_state_change_event(self.hass, entities, self._on_state_change)
            )
        self._recompute()

    async def async_will_remove_from_hass(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    @callback
    def _on_state_change(self, event) -> None:
        self._recompute()
        self.async_write_ha_state()

    def _resolve_offset_id(self, registry) -> str | None:
        raise NotImplementedError

    def _recompute(self) -> None:
        raise NotImplementedError


class BatteryTargetChargePowerSensor(_BatteryTargetPowerBase):
    """Sensor: max(0, round(pid + charge_offset))."""

    _attr_icon = "mdi:battery-charging"

    def __init__(self, entry_id: str, pid_entity_id: str, device_info: DeviceInfo) -> None:
        super().__init__(entry_id, pid_entity_id, device_info)
        self._attr_unique_id = f"{entry_id}_{UID_BATTERY_TARGET_CHARGE_POWER}"
        self._attr_name = "Target charge power"

    def _resolve_offset_id(self, registry) -> str | None:
        return registry.async_get_entity_id(
            "number", DOMAIN, f"{self._entry_id}_{UID_BATTERY_CHARGE_OFFSET}"
        )

    def _recompute(self) -> None:
        registry = er.async_get(self.hass)
        offset_id = self._resolve_offset_id(registry)
        pid = _state_float(self.hass, self._pid_entity_id)
        offset = _state_float(self.hass, offset_id)
        self._attr_native_value = float(max(0.0, round(pid + offset)))


class BatteryTargetDischargePowerSensor(_BatteryTargetPowerBase):
    """Sensor: abs(min(0, round(pid + discharge_offset)))."""

    _attr_icon = "mdi:battery-arrow-down"

    def __init__(self, entry_id: str, pid_entity_id: str, device_info: DeviceInfo) -> None:
        super().__init__(entry_id, pid_entity_id, device_info)
        self._attr_unique_id = f"{entry_id}_{UID_BATTERY_TARGET_DISCHARGE_POWER}"
        self._attr_name = "Target discharge power"

    def _resolve_offset_id(self, registry) -> str | None:
        return registry.async_get_entity_id(
            "number", DOMAIN, f"{self._entry_id}_{UID_BATTERY_DISCHARGE_OFFSET}"
        )

    def _recompute(self) -> None:
        registry = er.async_get(self.hass)
        offset_id = self._resolve_offset_id(registry)
        pid = _state_float(self.hass, self._pid_entity_id)
        offset = _state_float(self.hass, offset_id)
        self._attr_native_value = float(abs(min(0.0, round(pid + offset))))
