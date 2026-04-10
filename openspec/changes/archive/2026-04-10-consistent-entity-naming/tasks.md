## 1. Update UID constants in const.py

- [x] 1.1 Rename electricity number UID values: `electricity_green_energy_contribution_rate` → `electricity_tariff_green_energy_contribution`, `electricity_distribution_transport_rate` → `electricity_tariff_distribution_transport`, `electricity_excise_duty_rate` → `electricity_tariff_excise_duty`, `electricity_energy_contribution_rate` → `electricity_tariff_energy_contribution`, `electricity_vat_rate` → `electricity_vat`
- [x] 1.2 Rename gas number UID values: `gas_distribution_rate` → `gas_tariff_distribution`, `gas_transport_rate` → `gas_tariff_transport`, `gas_excise_duty_rate` → `gas_tariff_excise_duty`, `gas_energy_contribution_rate` → `gas_tariff_energy_contribution`, `gas_vat_rate` → `gas_vat`
- [x] 1.3 Rename electricity sensor UID values: `electricity_surcharge_rate` → `electricity_tariff_total_surcharge`, `electricity_surcharge_formula` → `electricity_tariff_total_surcharge_formula`, `electricity_price_import` → `electricity_current_price_import`, `electricity_price_export` → `electricity_current_price_export`, `electricity_price_import_eur` → `electricity_current_price_import_eur`, `electricity_price_export_eur` → `electricity_current_price_export_eur`
- [x] 1.4 Rename gas sensor UID values: `gas_surcharge_rate` → `gas_tariff_total_surcharge`, `gas_price` → `gas_current_price`

## 2. Update sensor.py display names

- [x] 2.1 Update `ElectricitySurchargeSensor._attr_name` to `"Total surcharge"`
- [x] 2.2 Update `ElectricitySurchargeFormulaSensor._attr_name` to `"Total surcharge formula"`
- [x] 2.3 Update `ElectricityImportPriceSensor._attr_name` to `"Current import price"`
- [x] 2.4 Update `ElectricityExportPriceSensor._attr_name` to `"Current export price"`
- [x] 2.5 Update `ElectricityImportPriceEurSensor._attr_name` to `"Current import price (EUR/kWh)"`
- [x] 2.6 Update `ElectricityExportPriceEurSensor._attr_name` to `"Current export price (EUR/kWh)"`
- [x] 2.7 Update `GasSurchargeSensor._attr_name` to `"Total surcharge"`
- [x] 2.8 Update `GasCurrentPriceSensor._attr_name` to `"Current price"`

## 3. Update strings.json and translations/en.json entity keys

- [x] 3.1 Update all `entity.number.*` keys in `strings.json` to match new number UIDs
- [x] 3.2 Update all `entity.sensor.*` keys in `strings.json` to match new sensor UIDs and English names
- [x] 3.3 Mirror all changes from `strings.json` into `translations/en.json`

## 4. Verify

- [x] 4.1 Confirm `sensor.py` `_attr_unique_id` and `entity_id` assignments match new UID constants (they derive from constants, so this is a consistency check)
- [x] 4.2 Confirm `number.py` descriptor `unique_id_suffix` values match new UID constants
- [x] 4.3 Check no old UID string literals remain anywhere in the codebase
