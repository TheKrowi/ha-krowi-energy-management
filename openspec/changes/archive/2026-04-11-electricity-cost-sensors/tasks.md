## 1. Constants

- [x] 1.1 Add 8 `CONF_ELECTRICITY_*` config key constants to `const.py`
- [x] 1.2 Add 8 `DEFAULT_ELECTRICITY_*` default entity ID constants to `const.py`
- [x] 1.3 Add 7 `UID_ELECTRICITY_*` unique ID constants to `const.py`
- [x] 1.4 Add 7 × 2 `NAMES` entries (EN + NL) for all new sensor entities to `const.py`

## 2. Config Flow

- [x] 2.1 Add 8 `vol.Optional` `EntitySelector()` fields to `_electricity_options_schema()` in `config_flow.py`

## 3. Per-Tariff Accumulator Sensors

- [x] 3.1 Implement `ElectricityImportCostT1Sensor` (RestoreEntity, TOTAL_INCREASING, EUR) in `sensor.py`
- [x] 3.2 Implement `ElectricityImportCostT2Sensor` (RestoreEntity, TOTAL_INCREASING, EUR) in `sensor.py`
- [x] 3.3 Implement `ElectricityExportRevenueT1Sensor` (RestoreEntity, TOTAL_INCREASING, EUR) in `sensor.py`
- [x] 3.4 Implement `ElectricityExportRevenueT2Sensor` (RestoreEntity, TOTAL_INCREASING, EUR) in `sensor.py`

## 4. Derived Aggregate Sensors

- [x] 4.1 Implement `ElectricityTotalImportCostSensor` (derived, TOTAL_INCREASING, EUR) in `sensor.py`
- [x] 4.2 Implement `ElectricityTotalExportRevenueSensor` (derived, TOTAL_INCREASING, EUR) in `sensor.py`
- [x] 4.3 Implement `ElectricityNetCostSensor` (derived, MEASUREMENT, EUR, can go negative) in `sensor.py`

## 5. Wire Up

- [x] 5.1 Read the 8 new config keys via `effective.get(key, DEFAULT_...)` in `async_setup_entry` (electricity branch)
- [x] 5.2 Instantiate all 7 new sensors and add them to the `entities` list in `async_setup_entry`
- [x] 5.3 Import all new UID and CONF constants in `sensor.py`
