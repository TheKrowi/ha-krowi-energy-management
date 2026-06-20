"""Battery management mode sensor for Krowi Energy Management."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity  # type: ignore
from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers.device_registry import DeviceInfo  # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback  # type: ignore

from .battery_manager import BatteryManager
from .const import DOMAIN, UID_BATTERY_MANAGEMENT_MODE


async def async_setup(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the battery management mode sensor."""
    manager: BatteryManager = hass.data[DOMAIN][f"battery_manager_{entry.entry_id}"]
    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
    )
    async_add_entities([BatteryManagementModeSensor(entry.entry_id, manager, device_info)])


class BatteryManagementModeSensor(SensorEntity):
    """Sensor that reflects the current battery control mode (idle/charging/discharging)."""

    _attr_should_poll = False
    _attr_icon = "mdi:battery-arrow-up-outline"

    def __init__(
        self,
        entry_id: str,
        manager: BatteryManager,
        device_info: DeviceInfo,
    ) -> None:
        self._manager = manager
        self._attr_device_info = device_info
        self._attr_unique_id = f"{entry_id}_{UID_BATTERY_MANAGEMENT_MODE}"
        self._attr_name = "Battery management mode"

    async def async_added_to_hass(self) -> None:
        """Subscribe to mode changes from the manager."""
        self._manager.add_mode_listener(self._on_mode_change)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from mode changes."""
        self._manager.remove_mode_listener(self._on_mode_change)

    def _on_mode_change(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return self._manager.mode
