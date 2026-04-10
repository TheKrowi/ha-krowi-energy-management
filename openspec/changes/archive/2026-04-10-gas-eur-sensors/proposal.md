## Why

The gas device currently exposes a `gas_current_price` sensor and a `gas_tariff_total_surcharge` sensor, but lacks the human-readable surcharge formula present on the electricity side and lacks a `EUR/kWh` bridge sensor needed by the HA Energy Dashboard. Without the EUR bridge the gas price cannot be wired into HA's energy cost tracking.

## What Changes

- Add `gas_tariff_total_surcharge_formula` sensor — human-readable string showing the four component surcharge values and their sum, mirroring `electricity_tariff_total_surcharge_formula`.
- Add `gas_current_price_eur` sensor — `gas_current_price` converted to `EUR/kWh` using the configured `gas_unit`, enabling use in the HA Energy Dashboard.

## Capabilities

### New Capabilities

- `gas-eur-sensors`: Formula sensor and EUR/kWh bridge sensor for the gas device, bringing gas to parity with the electricity EUR bridge pattern.

### Modified Capabilities

- `gas-sensors`: Two new sensor entities are added to the gas device (formula and EUR bridge). The existing `gas_tariff_total_surcharge` and `gas_current_price` sensors are unchanged.

## Impact

- `sensor.py`: Two new sensor classes (`GasSurchargeFormulaSensor`, `GasCurrentPriceEurSensor`); both registered in `async_setup_entry` for gas entries.
- `const.py`: Two new UID constants (`UID_GAS_SURCHARGE_FORMULA`, `UID_GAS_PRICE_EUR`); four new `NAMES` entries (EN + NL).
- No config flow changes, no new config keys, no breaking changes.
