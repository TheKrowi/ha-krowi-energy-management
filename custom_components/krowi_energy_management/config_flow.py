"""Config flow for Krowi Energy Management."""
from __future__ import annotations

import voluptuous as vol # type: ignore
from homeassistant import config_entries # type: ignore
from homeassistant.components import repairs as ir # type: ignore
from homeassistant.const import EVENT_HOMEASSISTANT_STOP # type: ignore
from homeassistant.core import callback # type: ignore
from homeassistant.helpers import entity_registry as er, selector # type: ignore

from .const import (
    CONF_DOMAIN_TYPE,
    CONF_ELECTRICITY_DSO,
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
    CONF_GOS_ZONE,
    CONF_LANGUAGE,
    CONF_LOW_PRICE_CUTOFF,
    CONF_SUPPLIER_LABEL,
    CONF_SUPPLIER_SLUG,
    DEFAULT_ELECTRICITY_DSO,
    DEFAULT_ELECTRICITY_EXPORT_T1_METER,
    DEFAULT_ELECTRICITY_EXPORT_T1_PRICE,
    DEFAULT_ELECTRICITY_EXPORT_T2_METER,
    DEFAULT_ELECTRICITY_EXPORT_T2_PRICE,
    DEFAULT_ELECTRICITY_IMPORT_T1_METER,
    DEFAULT_ELECTRICITY_IMPORT_T1_PRICE,
    DEFAULT_ELECTRICITY_IMPORT_T2_METER,
    DEFAULT_ELECTRICITY_IMPORT_T2_PRICE,
    DEFAULT_EXPORT_TEMPLATE,
    DEFAULT_GAS_METER_ENTITY,
    DEFAULT_GOS_ZONE,
    DEFAULT_LOW_PRICE_CUTOFF,
    DOMAIN,
    DOMAIN_TYPE_ELECTRICITY,
    DOMAIN_TYPE_ELECTRICITY_SUPPLIER,
    DOMAIN_TYPE_GAS,
    DOMAIN_TYPE_SETTINGS,
    ELECTRICITY_DSO_OPTIONS,
    ELECTRICITY_SUPPLIER_CATALOG,
    GOS_ZONE_OPTIONS,
    LANG_EN,
    LANGUAGE_OPTIONS,
)


def _electricity_schema(defaults: dict | None = None) -> vol.Schema:
    d = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_EXPORT_TEMPLATE,
                default=d.get(
                    CONF_EXPORT_TEMPLATE,
                    DEFAULT_EXPORT_TEMPLATE,
                ),
            ): str,
        }
    )


def _electricity_options_schema(defaults: dict | None = None) -> vol.Schema:
    d = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_ELECTRICITY_DSO,
                default=d.get(CONF_ELECTRICITY_DSO, DEFAULT_ELECTRICITY_DSO),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=ELECTRICITY_DSO_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_EXPORT_TEMPLATE,
                default=d.get(
                    CONF_EXPORT_TEMPLATE,
                    DEFAULT_EXPORT_TEMPLATE,
                ),
            ): str,
            vol.Optional(
                CONF_LOW_PRICE_CUTOFF,
                default=d.get(CONF_LOW_PRICE_CUTOFF, DEFAULT_LOW_PRICE_CUTOFF),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.0,
                    max=2.0,
                    step=0.01,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_ELECTRICITY_IMPORT_T1_METER,
                default=d.get(CONF_ELECTRICITY_IMPORT_T1_METER, DEFAULT_ELECTRICITY_IMPORT_T1_METER),
            ): selector.EntitySelector(),
            vol.Optional(
                CONF_ELECTRICITY_IMPORT_T2_METER,
                default=d.get(CONF_ELECTRICITY_IMPORT_T2_METER, DEFAULT_ELECTRICITY_IMPORT_T2_METER),
            ): selector.EntitySelector(),
            vol.Optional(
                CONF_ELECTRICITY_EXPORT_T1_METER,
                default=d.get(CONF_ELECTRICITY_EXPORT_T1_METER, DEFAULT_ELECTRICITY_EXPORT_T1_METER),
            ): selector.EntitySelector(),
            vol.Optional(
                CONF_ELECTRICITY_EXPORT_T2_METER,
                default=d.get(CONF_ELECTRICITY_EXPORT_T2_METER, DEFAULT_ELECTRICITY_EXPORT_T2_METER),
            ): selector.EntitySelector(),
            vol.Optional(
                CONF_ELECTRICITY_IMPORT_T1_PRICE,
                default=d.get(CONF_ELECTRICITY_IMPORT_T1_PRICE, DEFAULT_ELECTRICITY_IMPORT_T1_PRICE),
            ): selector.EntitySelector(),
            vol.Optional(
                CONF_ELECTRICITY_IMPORT_T2_PRICE,
                default=d.get(CONF_ELECTRICITY_IMPORT_T2_PRICE, DEFAULT_ELECTRICITY_IMPORT_T2_PRICE),
            ): selector.EntitySelector(),
            vol.Optional(
                CONF_ELECTRICITY_EXPORT_T1_PRICE,
                default=d.get(CONF_ELECTRICITY_EXPORT_T1_PRICE, DEFAULT_ELECTRICITY_EXPORT_T1_PRICE),
            ): selector.EntitySelector(),
            vol.Optional(
                CONF_ELECTRICITY_EXPORT_T2_PRICE,
                default=d.get(CONF_ELECTRICITY_EXPORT_T2_PRICE, DEFAULT_ELECTRICITY_EXPORT_T2_PRICE),
            ): selector.EntitySelector(),
        }
    )


def _gas_options_schema(defaults: dict | None = None) -> vol.Schema:
    d = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_GOS_ZONE,
                default=d.get(CONF_GOS_ZONE, DEFAULT_GOS_ZONE),
            ): vol.In(GOS_ZONE_OPTIONS),
            vol.Optional(
                CONF_GAS_METER_ENTITY,
                default=d.get(CONF_GAS_METER_ENTITY, DEFAULT_GAS_METER_ENTITY),
            ): selector.EntitySelector(),
        }
    )


def _gas_schema(defaults: dict | None = None) -> vol.Schema:
    return vol.Schema({})


class KrowiEnergyManagementConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Krowi Energy Management."""

    VERSION = 3

    async def async_step_user(self, user_input=None):
        """Delegate to menu step."""
        return await self.async_step_menu()

    async def async_step_menu(self, user_input=None):
        """Show domain picker menu."""
        return self.async_show_menu(
            step_id="menu",
            menu_options=[DOMAIN_TYPE_ELECTRICITY, DOMAIN_TYPE_GAS, DOMAIN_TYPE_SETTINGS, DOMAIN_TYPE_ELECTRICITY_SUPPLIER],
        )

    async def async_step_electricity(self, user_input=None):
        """Handle electricity domain setup."""
        # Duplicate check
        for entry in self._async_current_entries():
            if entry.data.get(CONF_DOMAIN_TYPE) == DOMAIN_TYPE_ELECTRICITY:
                return self.async_abort(reason="already_configured")

        if user_input is None:
            return self.async_show_form(
                step_id=DOMAIN_TYPE_ELECTRICITY,
                data_schema=_electricity_schema(),
            )

        return self.async_create_entry(
            title="Electricity",
            data={
                CONF_DOMAIN_TYPE: DOMAIN_TYPE_ELECTRICITY,
                **user_input,
            },
        )

    async def async_step_gas(self, user_input=None):
        """Handle gas domain setup."""
        # Duplicate check
        for entry in self._async_current_entries():
            if entry.data.get(CONF_DOMAIN_TYPE) == DOMAIN_TYPE_GAS:
                return self.async_abort(reason="already_configured")

        if user_input is None:
            return self.async_show_form(
                step_id=DOMAIN_TYPE_GAS,
                data_schema=_gas_schema(),
            )

        return self.async_create_entry(
            title="Gas",
            data={CONF_DOMAIN_TYPE: DOMAIN_TYPE_GAS},
        )

    async def async_step_electricity_supplier(self, user_input=None):
        """Handle electricity supplier entry setup."""
        if user_input is None:
            catalog_keys = list(ELECTRICITY_SUPPLIER_CATALOG.keys())
            return self.async_show_form(
                step_id=DOMAIN_TYPE_ELECTRICITY_SUPPLIER,
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_SUPPLIER_SLUG): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=catalog_keys,
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        ),
                        vol.Optional(CONF_SUPPLIER_LABEL, default=""): str,
                    }
                ),
            )

        slug = user_input[CONF_SUPPLIER_SLUG]
        label = user_input.get(CONF_SUPPLIER_LABEL, "").strip()
        catalog_entry = ELECTRICITY_SUPPLIER_CATALOG[slug]
        title = label if label else catalog_entry["name"]
        return self.async_create_entry(
            title=title,
            data={
                CONF_DOMAIN_TYPE: DOMAIN_TYPE_ELECTRICITY_SUPPLIER,
                CONF_SUPPLIER_SLUG: slug,
                CONF_SUPPLIER_LABEL: label or catalog_entry["name"],
            },
        )

    async def async_step_settings(self, user_input=None):
        """Handle settings entry setup."""
        for entry in self._async_current_entries():
            if entry.data.get(CONF_DOMAIN_TYPE) == DOMAIN_TYPE_SETTINGS:
                return self.async_abort(reason="already_configured")
        """Handle settings entry setup."""
        for entry in self._async_current_entries():
            if entry.data.get(CONF_DOMAIN_TYPE) == DOMAIN_TYPE_SETTINGS:
                return self.async_abort(reason="already_configured")

        if user_input is None:
            return self.async_show_form(
                step_id=DOMAIN_TYPE_SETTINGS,
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_LANGUAGE, default=LANG_EN): vol.In(LANGUAGE_OPTIONS),
                    }
                ),
            )

        return self.async_create_entry(
            title="Settings",
            data={
                CONF_DOMAIN_TYPE: DOMAIN_TYPE_SETTINGS,
                **user_input,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow."""
        return KrowiEnergyManagementOptionsFlow(config_entry)


class KrowiEnergyManagementOptionsFlow(config_entries.OptionsFlow):
    """Options flow for Krowi Energy Management."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input=None):
        """Route to domain-specific options step."""
        domain_type = self._entry.data.get(CONF_DOMAIN_TYPE)
        if domain_type == DOMAIN_TYPE_ELECTRICITY:
            return await self.async_step_electricity_options(user_input)
        if domain_type == DOMAIN_TYPE_SETTINGS:
            return await self.async_step_settings_options(user_input)
        if domain_type == DOMAIN_TYPE_ELECTRICITY_SUPPLIER:
            return await self.async_step_electricity_supplier_options(user_input)
        return await self.async_step_gas_options(user_input)

    async def async_step_settings_options(self, user_input=None):
        """Settings options — change language."""
        current = {**self._entry.data, **self._entry.options}

        if user_input is None:
            return self.async_show_form(
                step_id="settings_options",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_LANGUAGE, default=current.get(CONF_LANGUAGE, LANG_EN)
                        ): vol.In(LANGUAGE_OPTIONS),
                    }
                ),
            )

        # Reload all domain entries so they pick up the new language
        result = self.async_create_entry(title="", data=user_input)
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.data.get(CONF_DOMAIN_TYPE) in (DOMAIN_TYPE_ELECTRICITY, DOMAIN_TYPE_GAS):
                self.hass.async_create_task(
                    self.hass.config_entries.async_reload(entry.entry_id)
                )
        return result

    async def async_step_electricity_supplier_options(self, user_input=None):
        """Electricity supplier options — change display label."""
        current = {**self._entry.data, **self._entry.options}
        slug = current.get(CONF_SUPPLIER_SLUG, "")
        catalog_entry = ELECTRICITY_SUPPLIER_CATALOG.get(slug, {})
        default_label = catalog_entry.get("name", slug)

        if user_input is None:
            return self.async_show_form(
                step_id="electricity_supplier_options",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            CONF_SUPPLIER_LABEL,
                            default=current.get(CONF_SUPPLIER_LABEL, default_label),
                        ): str,
                    }
                ),
            )

        label = user_input.get(CONF_SUPPLIER_LABEL, "").strip() or default_label
        self.hass.config_entries.async_update_entry(self._entry, title=label)
        return self.async_create_entry(title="", data={CONF_SUPPLIER_LABEL: label})

    async def async_step_electricity_options(self, user_input=None):
        """Electricity options — pre-populated with current values."""
        current = {**self._entry.data, **self._entry.options}

        if user_input is None:
            return self.async_show_form(
                step_id="electricity_options",
                data_schema=_electricity_options_schema(current),
            )

        return self.async_create_entry(title="", data=user_input)

    async def async_step_gas_options(self, user_input=None):
        """Gas options — GOS zone and gas meter entity."""
        current = {**self._entry.data, **self._entry.options}

        if user_input is None:
            return self.async_show_form(
                step_id="gas_options",
                data_schema=_gas_options_schema(current),
            )

        return self.async_create_entry(title="", data=user_input)
