## 1. Constants

- [x] 1.1 Add `UID_GAS_SURCHARGE_FORMULA = "gas_tariff_total_surcharge_formula"` to `const.py`
- [x] 1.2 Add `UID_GAS_PRICE_EUR = "gas_current_price_eur"` to `const.py`
- [x] 1.3 Add NAMES entries for `UID_GAS_SURCHARGE_FORMULA` (EN: "Total surcharge formula", NL: "Totale toeslag formule") to `const.py`
- [x] 1.4 Add NAMES entries for `UID_GAS_PRICE_EUR` (EN: "Current price (EUR/kWh)", NL: "Actuele prijs (EUR/kWh)") to `const.py`

## 2. Formula Sensor

- [x] 2.1 Add `GasSurchargeFormulaSensor` class to `sensor.py`, mirroring `ElectricitySurchargeFormulaSensor` over the four gas rate UIDs
- [x] 2.2 Verify sensor has no `unit_of_measurement` and no `state_class`
- [x] 2.3 Verify default state is `"0.00000 + 0.00000 + 0.00000 + 0.00000 = 0.00000 <gas_unit>"`

## 3. EUR Bridge Sensor

- [x] 3.1 Add `GasCurrentPriceEurSensor` class to `sensor.py`, mirroring `ElectricityImportPriceEurSensor` using `UID_GAS_PRICE` as source
- [x] 3.2 Use `convert_unit(value, gas_unit, "EUR/kWh")` for the conversion (not a hard-coded divisor)
- [x] 3.3 Set `native_unit_of_measurement = "EUR/kWh"` and `state_class = SensorStateClass.MEASUREMENT`
- [x] 3.4 Verify sensor goes unavailable (`native_value = None`) when `gas_current_price` is unavailable

## 4. Registration

- [x] 4.1 Import `UID_GAS_SURCHARGE_FORMULA` and `UID_GAS_PRICE_EUR` in `sensor.py`
- [x] 4.2 Add `GasSurchargeFormulaSensor` and `GasCurrentPriceEurSensor` to the gas branch of `async_setup_entry` in `sensor.py`
- [x] 4.3 Verify both new sensors are associated with the `(DOMAIN, f"{entry_id}_gas")` device
