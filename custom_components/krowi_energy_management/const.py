"""Constants for Krowi Energy Management."""

DOMAIN = "krowi_energy_management"

# Unit options
UNIT_OPTIONS = ["c€/kWh", "€/kWh", "€/MWh"]
UNIT_ELECTRICITY = "c€/kWh"
GAS_UNIT = "c€/kWh"

# Config / options entry keys
CONF_DOMAIN_TYPE = "domain_type"
CONF_FX_RATE_ENTITY = "fx_rate_entity"
CONF_EXPORT_TEMPLATE = "export_template"
CONF_LOW_PRICE_CUTOFF = "low_price_cutoff"
DEFAULT_LOW_PRICE_CUTOFF = 1.0
DEFAULT_EXPORT_TEMPLATE = "{{ ((states('sensor.electricity_spot_average_price') | float(0) / 100 * 0.94 - 0.017) * 100) | round(5) }}"

# Domain type values
DOMAIN_TYPE_ELECTRICITY = "electricity"
DOMAIN_TYPE_GAS = "gas"

# Unique ID suffixes — electricity number entities
UID_ELECTRICITY_GREEN_ENERGY = "electricity_tariff_green_energy_contribution"
UID_ELECTRICITY_DISTRIBUTION_TRANSPORT = "electricity_tariff_distribution_transport"
UID_ELECTRICITY_EXCISE_DUTY = "electricity_tariff_excise_duty"
UID_ELECTRICITY_ENERGY_CONTRIBUTION = "electricity_tariff_energy_contribution"
UID_ELECTRICITY_VAT = "electricity_vat"

# Unique ID suffixes — gas number entities
UID_GAS_DISTRIBUTION = "gas_tariff_distribution"
UID_GAS_TRANSPORT = "gas_tariff_transport"
UID_GAS_EXCISE_DUTY = "gas_tariff_excise_duty"
UID_GAS_ENERGY_CONTRIBUTION = "gas_tariff_energy_contribution"
UID_GAS_VAT = "gas_vat"

# Unique ID suffixes — electricity sensors
UID_ELECTRICITY_SURCHARGE_RATE = "electricity_tariff_total_surcharge"
UID_ELECTRICITY_SURCHARGE_FORMULA = "electricity_tariff_total_surcharge_formula"
UID_ELECTRICITY_PRICE_IMPORT = "electricity_current_price_import"
UID_ELECTRICITY_PRICE_EXPORT = "electricity_current_price_export"

UID_ELECTRICITY_PRICE_IMPORT_EUR = "electricity_current_price_import_eur"
UID_ELECTRICITY_PRICE_EXPORT_EUR = "electricity_current_price_export_eur"
UID_ELECTRICITY_SPOT_CURRENT_PRICE = "electricity_spot_current_price"
UID_ELECTRICITY_SPOT_AVERAGE_PRICE = "electricity_spot_average_price"

# Unique ID suffixes — gas sensors
UID_GAS_SURCHARGE_RATE = "gas_tariff_total_surcharge"
UID_GAS_SURCHARGE_FORMULA = "gas_tariff_total_surcharge_formula"
UID_GAS_PRICE = "gas_current_price"
UID_GAS_PRICE_EUR = "gas_current_price_eur"
UID_GAS_SPOT_TODAY_PRICE = "gas_spot_today_price"
UID_GAS_SPOT_AVERAGE_PRICE = "gas_spot_average_price"
UID_GAS_CALORIFIC_VALUE = "gas_calorific_value"
UID_GAS_PRICE_M3 = "gas_current_price_m3"
UID_GAS_CONSUMPTION_KWH = "gas_consumption_kwh"

# Dispatcher signals
SIGNAL_NORDPOOL_UPDATE = "krowi_energy_management_nordpool_update"
SIGNAL_TTF_DAM_UPDATE = "krowi_energy_management_ttf_dam_update"
SIGNAL_GCV_UPDATE = "krowi_energy_management_gcv_update"

# GCV / gas meter config keys and defaults
CONF_GOS_ZONE = "gos_zone"
DEFAULT_GOS_ZONE = "GOS FLUVIUS - LEUVEN"
CONF_GAS_METER_ENTITY = "gas_meter_entity"
DEFAULT_GAS_METER_ENTITY = "sensor.gas_meter_consumption"

# Atrias GCV API
ATRIAS_GCV_API_URL = "https://api.atrias.be/roots/download/"
ATRIAS_SUBSCRIPTION_KEY = "41be1fbab53b4a80ba0d17084a338a55"

# Belgian GOS zone options (alphabetical, from Atrias GCV files)
GOS_ZONE_OPTIONS: list[str] = [
    "GOS FLUVIUS - AALST",
    "GOS FLUVIUS - ANTWERPEN",
    "GOS FLUVIUS - ANTWERPEN SCHELDELAAN",
    "GOS FLUVIUS - BERINGEN",
    "GOS FLUVIUS - BEVEREN",
    "GOS FLUVIUS - GENT",
    "GOS FLUVIUS - GENT MANUPORT",
    "GOS FLUVIUS - GOOIK",
    "GOS FLUVIUS - HASSELT",
    "GOS FLUVIUS - KORTRIJK",
    "GOS FLUVIUS - LEUVEN",
    "GOS FLUVIUS - LIEDEKERKE",
    "GOS FLUVIUS - OOSTENDE",
    "GOS FLUVIUS - STEENOKKERZEEL",
    "GOS FLUVIUS - VILVOORDE",
    "GOS FLUVIUS - ZAVENTEM",
    "GOS FLUVIUS - ZELZATE",
    "GOS FLUVIUS-ORES HALLE BRAINE-NVL",
    "IDEG EGHEZEE (GOS)",
    "IDEG ISNES (GOS)",
    "IDEG METTET (GOS)",
    "IDEG NAMUR (GOS)",
    "IDEG ROCHEFORT (GOS)",
    "IDEG VEHIRE (GOS)",
    "IGH ATH-LEUZE (GOS)",
    "IGH BAUDOUR AVOCAT (GOS)",
    "IGH ELLEZELLES (GOS)",
    "IGH ENGHIEN (GOS)",
    "IGH HENSIES THULIN (GOS)",
    "IGH MONS-CHARLEROI (GOS)",
    "IGH QUEVAUCAMPS (GOS)",
    "IGH QUIEVRAIN (GOS)",
    "IGH SIRAULT (GOS)",
    "IGH SOIGNIES (GOS)",
    "IGH TOURNAI (GOS)",
    "INTERLUX ARLON (GOS)",
    "INTERLUX AUBANGE (GOS)",
    "INTERLUX AYE (GOS)",
    "INTERLUX BASTOGNE (GOS)",
    "INTERLUX LIBRAMONT (GOS)",
    "INTERLUX NEUFCHÂTEAU (GOS)",
    "INTERLUX VIELSALM (GOS)",
    "IVERLEK DILBEEK (GOS)",
    "RESA AMAY (GOS)",
    "RESA ANDENNE (GOS)",
    "RESA ENGIS (GOS)",
    "RESA EST (GOS)",
    "RESA HANNUT (GOS)",
    "RESA HERMALLE-SOUS-HUY (GOS)",
    "RESA HUY (GOS)",
    "RESA LIEGE (GOS)",
    "RESA SPIME (GOS)",
    "RESA ST.-GEORGES-SUR-MEUSE (GOS)",
    "RESA VERVIERS (GOS)",
    "RESA VILLERS-LE-BOUILLET (GOS)",
    "SEDILEC ECAUSSINNES (GOS)",
    "SEDILEC GENAPPE (GOS)",
    "SEDILEC HENNUYERES (GOS)",
    "SEDILEC VIRGINAL (GOS)",
    "SIBELGA QUAI (GOS)",
    "SRA FLUVIUS-ORES OVERIJSE \u2013 GBLX",
]

# Repairs issue ID template
ISSUE_ENTITY_RENAMED = "entity_renamed_{entry_id}"

# Settings entry domain type
DOMAIN_TYPE_SETTINGS = "settings"

# Language config key and options
CONF_LANGUAGE = "language"
LANG_EN = "en"
LANG_NL = "nl"
LANGUAGE_OPTIONS = [LANG_EN, LANG_NL]

# Display names keyed by (unique_id_suffix, language)
NAMES: dict[tuple[str, str], str] = {
    # Electricity number entities
    (UID_ELECTRICITY_GREEN_ENERGY, LANG_EN): "Green energy contribution",
    (UID_ELECTRICITY_GREEN_ENERGY, LANG_NL): "Groene stroom bijdrage",
    (UID_ELECTRICITY_DISTRIBUTION_TRANSPORT, LANG_EN): "Distribution & transport",
    (UID_ELECTRICITY_DISTRIBUTION_TRANSPORT, LANG_NL): "Distributie & transport",
    (UID_ELECTRICITY_EXCISE_DUTY, LANG_EN): "Excise duty",
    (UID_ELECTRICITY_EXCISE_DUTY, LANG_NL): "Bijzondere accijns",
    (UID_ELECTRICITY_ENERGY_CONTRIBUTION, LANG_EN): "Energy contribution",
    (UID_ELECTRICITY_ENERGY_CONTRIBUTION, LANG_NL): "Energiebijdrage",
    (UID_ELECTRICITY_VAT, LANG_EN): "VAT",
    (UID_ELECTRICITY_VAT, LANG_NL): "BTW",
    # Gas number entities
    (UID_GAS_DISTRIBUTION, LANG_EN): "Distribution",
    (UID_GAS_DISTRIBUTION, LANG_NL): "Distributie",
    (UID_GAS_TRANSPORT, LANG_EN): "Transport (Fluxys)",
    (UID_GAS_TRANSPORT, LANG_NL): "Transport (Fluxys)",
    (UID_GAS_EXCISE_DUTY, LANG_EN): "Excise duty",
    (UID_GAS_EXCISE_DUTY, LANG_NL): "Bijzondere accijns",
    (UID_GAS_ENERGY_CONTRIBUTION, LANG_EN): "Energy contribution",
    (UID_GAS_ENERGY_CONTRIBUTION, LANG_NL): "Energiebijdrage",
    (UID_GAS_VAT, LANG_EN): "VAT",
    (UID_GAS_VAT, LANG_NL): "BTW",
    # Electricity sensor entities
    (UID_ELECTRICITY_SURCHARGE_RATE, LANG_EN): "Total surcharge",
    (UID_ELECTRICITY_SURCHARGE_RATE, LANG_NL): "Totale toeslag",
    (UID_ELECTRICITY_SURCHARGE_FORMULA, LANG_EN): "Total surcharge formula",
    (UID_ELECTRICITY_SURCHARGE_FORMULA, LANG_NL): "Totale toeslag formule",
    (UID_ELECTRICITY_PRICE_IMPORT, LANG_EN): "Current import price",
    (UID_ELECTRICITY_PRICE_IMPORT, LANG_NL): "Actuele importprijs",
    (UID_ELECTRICITY_PRICE_EXPORT, LANG_EN): "Current export price",
    (UID_ELECTRICITY_PRICE_EXPORT, LANG_NL): "Actuele exportprijs",
    (UID_ELECTRICITY_PRICE_IMPORT_EUR, LANG_EN): "Current import price (EUR/kWh)",
    (UID_ELECTRICITY_PRICE_IMPORT_EUR, LANG_NL): "Actuele importprijs (EUR/kWh)",
    (UID_ELECTRICITY_PRICE_EXPORT_EUR, LANG_EN): "Current export price (EUR/kWh)",
    (UID_ELECTRICITY_PRICE_EXPORT_EUR, LANG_NL): "Actuele exportprijs (EUR/kWh)",
    # Electricity spot sensors
    (UID_ELECTRICITY_SPOT_CURRENT_PRICE, LANG_EN): "Current price (EPEX SPOT)",
    (UID_ELECTRICITY_SPOT_CURRENT_PRICE, LANG_NL): "Huidige prijs (EPEX SPOT)",
    (UID_ELECTRICITY_SPOT_AVERAGE_PRICE, LANG_EN): "Monthly average price (EPEX SPOT)",
    (UID_ELECTRICITY_SPOT_AVERAGE_PRICE, LANG_NL): "Gemiddelde maandprijs (EPEX SPOT)",
    # Gas sensor entities
    (UID_GAS_SURCHARGE_RATE, LANG_EN): "Total surcharge",
    (UID_GAS_SURCHARGE_RATE, LANG_NL): "Totale toeslag",
    (UID_GAS_SURCHARGE_FORMULA, LANG_EN): "Total surcharge formula",
    (UID_GAS_SURCHARGE_FORMULA, LANG_NL): "Totale toeslag formule",
    (UID_GAS_PRICE, LANG_EN): "Current price",
    (UID_GAS_PRICE, LANG_NL): "Actuele prijs",
    (UID_GAS_PRICE_EUR, LANG_EN): "Current price (EUR/kWh)",
    (UID_GAS_PRICE_EUR, LANG_NL): "Actuele prijs (EUR/kWh)",
    # Gas spot sensor entities
    (UID_GAS_SPOT_TODAY_PRICE, LANG_EN): "Daily price (TTF DAM)",
    (UID_GAS_SPOT_TODAY_PRICE, LANG_NL): "Dagprijs (TTF DAM)",
    (UID_GAS_SPOT_AVERAGE_PRICE, LANG_EN): "Monthly average price (TTF DAM)",
    (UID_GAS_SPOT_AVERAGE_PRICE, LANG_NL): "Gemiddelde maandprijs (TTF DAM)",
    # Gas GCV and m³ sensor entities
    (UID_GAS_CALORIFIC_VALUE, LANG_EN): "Calorific value",
    (UID_GAS_CALORIFIC_VALUE, LANG_NL): "Calorische waarde",
    (UID_GAS_PRICE_M3, LANG_EN): "Current price (m³)",
    (UID_GAS_PRICE_M3, LANG_NL): "Actuele prijs (m³)",
    (UID_GAS_CONSUMPTION_KWH, LANG_EN): "Gas consumption",
    (UID_GAS_CONSUMPTION_KWH, LANG_NL): "Gasverbruik",
}
