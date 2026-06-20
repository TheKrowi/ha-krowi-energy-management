"""Battery management enabled switch for Krowi Energy Management."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity  # type: ignore
from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers.device_registry import DeviceInfo  # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback  # type: ignore
from homeassistant.helpers.restore_state import RestoreEntity  # type: ignore

from .battery_manager import BatteryManager
from .const import DOMAIN, UID_BATTERY_MANAGEMENT_ENABLED


async def async_setup(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the battery management enabled switch."""
    manager: BatteryManager = hass.data[DOMAIN][f"battery_manager_{entry.entry_id}"]
    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
    )
    async_add_entities([BatteryManagementEnabledSwitch(entry.entry_id, manager, device_info)])


class BatteryManagementEnabledSwitch(SwitchEntity, RestoreEntity):
    """Switch that pauses or resumes the battery management control loop."""

    _attr_should_poll = False
    _attr_icon = "mdi:battery-sync"

    def __init__(
        self,
        entry_id: str,
        manager: BatteryManager,
        device_info: DeviceInfo,
    ) -> None:
        self._manager = manager
        self._attr_device_info = device_info
        self._attr_unique_id = f"{entry_id}_{UID_BATTERY_MANAGEMENT_ENABLED}"
        self._attr_name = "Battery management enabled"

    async def async_added_to_hass(self) -> None:
        """Restore state on startup."""
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._manager.set_enabled(last_state.state != "off")
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return self._manager.enabled

    async def async_turn_on(self, **kwargs) -> None:
        self._manager.set_enabled(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._manager.set_enabled(False)
        self.async_write_ha_state()
