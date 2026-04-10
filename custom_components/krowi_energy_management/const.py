"""Constants for Krowi Energy Management."""

DOMAIN = "krowi_energy_management"

# Unit options
UNIT_OPTIONS = ["c€/kWh", "€/kWh", "€/MWh"]
UNIT_ELECTRICITY = "c€/kWh"

# Config / options entry keys
CONF_DOMAIN_TYPE = "domain_type"
CONF_UNIT = "unit"
CONF_CURRENT_PRICE_ENTITY = "current_price_entity"
CONF_FX_RATE_ENTITY = "fx_rate_entity"
CONF_EXPORT_TEMPLATE = "export_template"

# Domain type values
DOMAIN_TYPE_ELECTRICITY = "electricity"
DOMAIN_TYPE_GAS = "gas"

# Default entity IDs
DEFAULT_ELECTRICITY_PRICE_ENTITY = "sensor.nord_pool_be_current_price"
DEFAULT_GAS_PRICE_ENTITY = "sensor.krowi_ttf_dam_30d_avg"

# Unique ID suffixes — electricity number entities
UID_ELECTRICITY_GREEN_ENERGY = "electricity_green_energy_contribution_rate"
UID_ELECTRICITY_DISTRIBUTION_TRANSPORT = "electricity_distribution_transport_rate"
UID_ELECTRICITY_EXCISE_DUTY = "electricity_excise_duty_rate"
UID_ELECTRICITY_ENERGY_CONTRIBUTION = "electricity_energy_contribution_rate"
UID_ELECTRICITY_VAT = "electricity_vat_rate"

# Unique ID suffixes — gas number entities
UID_GAS_DISTRIBUTION = "gas_distribution_rate"
UID_GAS_TRANSPORT = "gas_transport_rate"
UID_GAS_EXCISE_DUTY = "gas_excise_duty_rate"
UID_GAS_ENERGY_CONTRIBUTION = "gas_energy_contribution_rate"
UID_GAS_VAT = "gas_vat_rate"

# Unique ID suffixes — electricity sensors
UID_ELECTRICITY_SURCHARGE_RATE = "electricity_surcharge_rate"
UID_ELECTRICITY_SURCHARGE_FORMULA = "electricity_surcharge_formula"
UID_ELECTRICITY_PRICE_IMPORT = "electricity_price_import"
UID_ELECTRICITY_PRICE_EXPORT = "electricity_price_export"

UID_ELECTRICITY_PRICE_IMPORT_EUR = "electricity_price_import_eur"
UID_ELECTRICITY_PRICE_EXPORT_EUR = "electricity_price_export_eur"

# Unique ID suffixes — gas sensors
UID_GAS_SURCHARGE_RATE = "gas_surcharge_rate"
UID_GAS_PRICE = "gas_price"

# Repairs issue ID template
ISSUE_ENTITY_RENAMED = "entity_renamed_{entry_id}"
