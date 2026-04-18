"""Tests for KrowiEnergyManagementConfigFlow and OptionsFlow routing."""
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from custom_components.krowi_energy_management.config_flow import (
    KrowiEnergyManagementConfigFlow,
    KrowiEnergyManagementOptionsFlow,
)
from custom_components.krowi_energy_management.const import (
    CONF_DOMAIN_TYPE,
    CONF_EXPORT_TEMPLATE,
    CONF_LANGUAGE,
    CONF_SUPPLIER_SLUG,
    CONF_SUPPLIER_LABEL,
    DOMAIN,
    DOMAIN_TYPE_ELECTRICITY,
    DOMAIN_TYPE_ELECTRICITY_SUPPLIER,
    DOMAIN_TYPE_GAS,
    DOMAIN_TYPE_SETTINGS,
    DEFAULT_EXPORT_TEMPLATE,
    LANG_EN,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_flow() -> KrowiEnergyManagementConfigFlow:
    """Return a ConfigFlow instance with a minimal hass mock."""
    flow = KrowiEnergyManagementConfigFlow()
    flow.hass = MagicMock()
    flow.hass.data = {DOMAIN: {}}
    # No existing entries by default
    flow._async_current_entries = MagicMock(return_value=[])
    # Minimal HA flow plumbing
    flow.context = {}
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    flow.async_abort = MagicMock(return_value={"type": "abort"})
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    flow.async_show_menu = MagicMock(return_value={"type": "menu"})
    return flow


def _make_entry(domain_type: str) -> MagicMock:
    entry = MagicMock()
    entry.data = {CONF_DOMAIN_TYPE: domain_type}
    return entry


def _make_options_flow(domain_type: str) -> KrowiEnergyManagementOptionsFlow:
    entry = _make_entry(domain_type)
    entry.options = {}
    flow = KrowiEnergyManagementOptionsFlow(entry)
    flow.hass = MagicMock()
    flow.hass.config_entries.async_entries.return_value = []
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    return flow


# ---------------------------------------------------------------------------
# ConfigFlow — async_step_electricity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_configFlow_electricityNoDuplicate_showsForm():
    # Given: no existing entries
    flow = _make_flow()

    # When: no user_input yet
    result = await flow.async_step_electricity(user_input=None)

    # Then
    flow.async_show_form.assert_called_once()
    assert result["type"] == "form"


@pytest.mark.asyncio
async def test_configFlow_electricityDuplicateExists_abortsAlreadyConfigured():
    # Given: existing electricity entry already present
    flow = _make_flow()
    flow._async_current_entries = MagicMock(
        return_value=[_make_entry(DOMAIN_TYPE_ELECTRICITY)]
    )

    # When
    result = await flow.async_step_electricity(user_input=None)

    # Then
    flow.async_abort.assert_called_once_with(reason="already_configured")
    assert result["type"] == "abort"


@pytest.mark.asyncio
async def test_configFlow_electricityValidInput_createsEntry():
    # Given
    flow = _make_flow()
    user_input = {CONF_EXPORT_TEMPLATE: "{{ states('sensor.spot') }}"}

    # When
    result = await flow.async_step_electricity(user_input=user_input)

    # Then
    flow.async_create_entry.assert_called_once()
    call_kwargs = flow.async_create_entry.call_args
    data = call_kwargs.kwargs.get("data") or call_kwargs.args[1] if call_kwargs.args else call_kwargs.kwargs["data"]
    assert data[CONF_DOMAIN_TYPE] == DOMAIN_TYPE_ELECTRICITY
    assert result["type"] == "create_entry"


# ---------------------------------------------------------------------------
# OptionsFlow — async_step_init routing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_optionsFlow_initElectricity_routesToElectricityOptions():
    # Given
    flow = _make_options_flow(DOMAIN_TYPE_ELECTRICITY)

    # When: call init with None (to show form)
    result = await flow.async_step_init(user_input=None)

    # Then: electricity options form shown
    flow.async_show_form.assert_called_once()
    assert result["type"] == "form"


@pytest.mark.asyncio
async def test_optionsFlow_initGas_routesToGasOptions():
    # Given
    flow = _make_options_flow(DOMAIN_TYPE_GAS)

    # When
    result = await flow.async_step_init(user_input=None)

    # Then
    flow.async_show_form.assert_called_once()
    assert result["type"] == "form"


@pytest.mark.asyncio
async def test_optionsFlow_initSettings_routesToSettingsOptions():
    # Given
    flow = _make_options_flow(DOMAIN_TYPE_SETTINGS)

    # When
    result = await flow.async_step_init(user_input=None)

    # Then
    flow.async_show_form.assert_called_once()
    assert result["type"] == "form"
