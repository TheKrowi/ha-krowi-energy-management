## Why

The HA Energy Dashboard requires electricity price sensors to use `EUR/kWh` (or other `EUR/<energy unit>` variants), but the component's electricity price sensors output `c€/kWh` which matches Belgian energy bills. Two bridge sensors are needed to expose `EUR/kWh` equivalents that the Energy Dashboard can consume. Additionally, the electricity unit is being locked to `c€/kWh` — hardcoded rather than user-selected — since it is the natural scale for Belgian tariffs and no other unit makes sense for this component's target audience.

## What Changes

- **BREAKING**: Remove the `unit` field from the electricity config flow and options flow. Electricity unit is now hardcoded to `c€/kWh`.
- **BREAKING**: Electricity config entries that have a stored `unit` value will no longer use it; the constant `c€/kWh` is used instead.
- Add two new sensor entities to the electricity config entry:
  - `electricity_price_import_eur` — import price in `EUR/kWh` (= import price ÷ 100), for use in the HA Energy Dashboard.
  - `electricity_price_export_eur` — export price in `EUR/kWh` (= export price ÷ 100), for use in the HA Energy Dashboard.
- The two new bridge sensors listen reactively to `electricity_price_import` and `electricity_price_export` respectively and propagate `unavailable`/`unknown` states.

## Capabilities

### New Capabilities
- `electricity-eur-bridge-sensors`: Two derived `EUR/kWh` sensor entities that expose import and export electricity prices in the unit expected by the HA Energy Dashboard, derived reactively from the existing `c€/kWh` price sensors.

### Modified Capabilities
- `electricity-tariff-entities`: The `unit` selector is removed from the electricity config/options flow. Electricity tariff number entities are always in `c€/kWh`.

## Impact

- `const.py` — add 2 new UID constants; add `UNIT_ELECTRICITY = "c€/kWh"` constant; `UNIT_OPTIONS` becomes gas-only or removed from electricity path.
- `config_flow.py` — remove `unit` vol schema field and selector from electricity step and electricity options step.
- `number.py` — electricity number entities always use `c€/kWh`; no longer read `unit` from config entry for electricity.
- `sensor.py` — add `ElectricityImportPriceEurSensor` and `ElectricityExportPriceEurSensor` classes.
- `strings.json` + `translations/en.json` — add entity names for the 2 new sensors.
