"""Number entities for Krowi Energy Management."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberMode, RestoreNumber # type: ignore
from homeassistant.config_entries import ConfigEntry # type: ignore
from homeassistant.core import HomeAssistant # type: ignore
from homeassistant.helpers.device_registry import DeviceInfo # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback # type: ignore

from .const import (
    CONF_DOMAIN_TYPE,
    DOMAIN,
    DOMAIN_TYPE_ELECTRICITY,
    DOMAIN_TYPE_GAS,
    GAS_UNIT,
    LANG_EN,
    NAMES,
    UNIT_ELECTRICITY,
    UID_ELECTRICITY_DISTRIBUTION_TRANSPORT,
    UID_ELECTRICITY_ENERGY_CONTRIBUTION,
    UID_ELECTRICITY_EXCISE_DUTY,
    UID_ELECTRICITY_GREEN_ENERGY,
    UID_ELECTRICITY_VAT,
    UID_GAS_DISTRIBUTION,
    UID_GAS_ENERGY_CONTRIBUTION,
    UID_GAS_EXCISE_DUTY,
    UID_GAS_TRANSPORT,
    UID_GAS_VAT,
)
from .utils import get_language


@dataclass
class _NumberDescriptor:
    unique_id_suffix: str
    unit: str  # percent sign or placeholder replaced at runtime
    min_value: float
    max_value: float
    step: float


_ELECTRICITY_DESCRIPTORS: list[_NumberDescriptor] = [
    _NumberDescriptor(UID_ELECTRICITY_GREEN_ENERGY, "UNIT", 0, 9999, 0.00001),
    _NumberDescriptor(UID_ELECTRICITY_DISTRIBUTION_TRANSPORT, "UNIT", 0, 9999, 0.00001),
    _NumberDescriptor(UID_ELECTRICITY_EXCISE_DUTY, "UNIT", 0, 9999, 0.00001),
    _NumberDescriptor(UID_ELECTRICITY_ENERGY_CONTRIBUTION, "UNIT", 0, 9999, 0.00001),
    _NumberDescriptor(UID_ELECTRICITY_VAT, "%", 0, 100, 0.01),
]

_GAS_DESCRIPTORS: list[_NumberDescriptor] = [
    _NumberDescriptor(UID_GAS_DISTRIBUTION, "UNIT", 0, 9999, 0.00001),
    _NumberDescriptor(UID_GAS_TRANSPORT, "UNIT", 0, 9999, 0.00001),
    _NumberDescriptor(UID_GAS_EXCISE_DUTY, "UNIT", 0, 9999, 0.00001),
    _NumberDescriptor(UID_GAS_ENERGY_CONTRIBUTION, "UNIT", 0, 9999, 0.00001),
    _NumberDescriptor(UID_GAS_VAT, "%", 0, 100, 0.01),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities for this config entry."""
    domain_type = entry.data[CONF_DOMAIN_TYPE]
    language = get_language(hass)

    if domain_type == DOMAIN_TYPE_ELECTRICITY:
        unit = UNIT_ELECTRICITY
        descriptors = _ELECTRICITY_DESCRIPTORS
        device_suffix = "electricity"
        device_name = "Electricity"
    elif domain_type == DOMAIN_TYPE_GAS:
        unit = GAS_UNIT
        descriptors = _GAS_DESCRIPTORS
        device_suffix = "gas"
        device_name = "Gas"
    else:
        return

    device_info = DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{device_suffix}")},
        name=device_name,
    )

    entities = [
        KrowiNumberEntity(
            entry_id=entry.entry_id,
            descriptor=desc,
            unit=unit if desc.unit == "UNIT" else desc.unit,
            device_info=device_info,
            language=language,
        )
        for desc in descriptors
    ]
    async_add_entities(entities)


class KrowiNumberEntity(RestoreNumber, NumberEntity):
    """A tariff rate number entity with value persistence."""

    _attr_mode = NumberMode.BOX
    _attr_should_poll = False

    def __init__(
        self,
        entry_id: str,
        descriptor: _NumberDescriptor,
        unit: str,
        device_info: DeviceInfo,
        language: str = LANG_EN,
    ) -> None:
        self._attr_unique_id = descriptor.unique_id_suffix
        self.entity_id = f"number.{descriptor.unique_id_suffix}"
        self._attr_name = NAMES.get((descriptor.unique_id_suffix, language), NAMES[(descriptor.unique_id_suffix, LANG_EN)])
        self._attr_native_unit_of_measurement = unit
        self._attr_native_min_value = descriptor.min_value
        self._attr_native_max_value = descriptor.max_value
        self._attr_native_step = descriptor.step
        self._attr_device_info = device_info
        self._attr_native_value: float = 0.0

    async def async_added_to_hass(self) -> None:
        """Restore previous value or default to 0."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_number_data()
        if last_state is not None and last_state.native_value is not None:
            self._attr_native_value = last_state.native_value
        else:
            self._attr_native_value = 0.0

    async def async_set_native_value(self, value: float) -> None:
        """Update and persist the value."""
        self._attr_native_value = value
        self.async_write_ha_state()
