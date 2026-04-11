## 1. Constants

- [x] 1.1 Add `UID_GAS_TOTAL_COST = "gas_total_cost"` to `const.py`
- [x] 1.2 Add `NAMES` entries for `(UID_GAS_TOTAL_COST, LANG_EN)` and `(UID_GAS_TOTAL_COST, LANG_NL)` in `const.py`

## 2. Sensor Implementation

- [x] 2.1 Add `UID_GAS_TOTAL_COST` to imports in `sensor.py`
- [x] 2.2 Implement `GasTotalCostSensor(KrowiSensor, RestoreEntity)` class in `sensor.py` with:
  - `_attr_state_class = SensorStateClass.TOTAL_INCREASING`
  - `_attr_device_class = SensorDeviceClass.MONETARY`
  - `_attr_native_unit_of_measurement = "EUR"`
  - `_attr_icon = "mdi:cash-multiple"`
  - Instance variables: `_last_m3: float | None`, `_last_known_price: float | None`
- [x] 2.3 Implement `async_added_to_hass`: restore prior `native_value` via `RestoreEntity`, anchor `_last_m3` to current meter reading, subscribe to `gas_meter_entity` state changes
- [x] 2.4 Implement `_handle_state_change` and `_update` with all guards: unavailable meter (skip), negative delta (re-anchor, skip), no GCV (skip), price fallback to `_last_known_price`, skip only when both price and last known price are unavailable
- [x] 2.5 Update `_last_known_price` whenever a valid price is read

## 3. Registration

- [x] 3.1 Add `GasTotalCostSensor(hass, entry_id, gas_meter_entity, device_info, language)` to the gas entities list in `async_setup_entry`
