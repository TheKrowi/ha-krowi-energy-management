## 1. Constants

- [x] 1.1 Add `UNIT_ELECTRICITY = "c€/kWh"` constant to `const.py`
- [x] 1.2 Add `UID_ELECTRICITY_PRICE_IMPORT_EUR` and `UID_ELECTRICITY_PRICE_EXPORT_EUR` UID suffix constants to `const.py`

## 2. Config Flow — Remove Electricity Unit Selector

- [x] 2.1 Remove `vol.Required(CONF_UNIT, ...)` from `_electricity_schema()` in `config_flow.py`
- [x] 2.2 Remove `CONF_UNIT` from electricity options schema in `KrowiEnergyManagementOptionsFlow`
- [x] 2.3 Remove any import of `UNIT_OPTIONS` from `config_flow.py` if it is no longer used there
- [x] 2.4 Remove the `unit` description strings from the electricity steps in `strings.json` and `translations/en.json`

## 3. Number Entities — Hardcode Electricity Unit

- [x] 3.1 In `number.py` `async_setup_entry`, replace `unit = effective[CONF_UNIT]` for the electricity branch with `unit = UNIT_ELECTRICITY` (imported from `const.py`)
- [x] 3.2 Remove the `CONF_UNIT` import from `number.py` if it is no longer used

## 4. Sensor Entities — Bridge Sensors

- [x] 4.1 Add `ElectricityImportPriceEurSensor` class to `sensor.py`: unique ID `UID_ELECTRICITY_PRICE_IMPORT_EUR`, `native_unit_of_measurement = "EUR/kWh"`, listens to `electricity_price_import` via `async_track_state_change_event`, divides float state by 100 rounded to 5 decimal places, sets `None` if source is non-numeric
- [x] 4.2 Add `ElectricityExportPriceEurSensor` class to `sensor.py`: same pattern as import, listening to `electricity_price_export`
- [x] 4.3 In `async_setup_entry` for the electricity branch in `sensor.py`, instantiate and append both new bridge sensors to the `entities` list
- [x] 4.4 Import the two new UID constants in `sensor.py`

## 5. Sensor — Fix Hardcoded Unit for Existing Electricity Price Sensors

- [x] 5.1 In `sensor.py` electricity branch of `async_setup_entry`, replace `unit = effective[CONF_UNIT]` (or equivalent) with `unit = UNIT_ELECTRICITY` for the existing `ElectricitySurchargeSensor`, `ElectricityImportPriceSensor`, and `ElectricityExportPriceSensor`
- [x] 5.2 Remove the `CONF_UNIT` import from `sensor.py` if it is no longer used

## 6. Translations

- [x] 6.1 Add entity name entries for `electricity_price_import_eur` and `electricity_price_export_eur` in `strings.json` under `entity.sensor`
- [x] 6.2 Add the same entries to `translations/en.json`
