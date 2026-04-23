"""Base sensor class and entity-registry helper for Krowi Energy Management."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers import entity_registry as er  # type: ignore
from homeassistant.helpers.device_registry import DeviceInfo  # type: ignore
from homeassistant.helpers.event import async_track_state_change_event  # type: ignore

from .const import DOMAIN


def _resolve_entity_id(hass: HomeAssistant, platform: str, unique_id: str) -> str | None:
    """Look up the current entity_id for a unique_id via the entity registry."""
    registry = er.async_get(hass)
    return registry.async_get_entity_id(platform, DOMAIN, unique_id)


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
