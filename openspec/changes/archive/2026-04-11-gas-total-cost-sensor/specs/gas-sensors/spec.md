## MODIFIED Requirements

### Requirement: Gas sensors grouped under Gas device
All gas sensor entities SHALL return a `DeviceInfo` that places them under the shared Gas device.

The device identifier SHALL be `(DOMAIN, f"{entry_id}_gas")`.

All gas sensor entities (`gas_tariff_total_surcharge`, `gas_tariff_total_surcharge_formula`, `gas_current_price`, `gas_current_price_eur`, `gas_spot_today_price`, `gas_spot_average_price`, `gas_calorific_value`, `gas_current_price_m3`, `gas_consumption_kwh`, `gas_total_cost`) SHALL be associated with this device.

#### Scenario: Gas sensors grouped under Gas device
- **WHEN** the gas config entry is set up
- **THEN** all gas sensor entities SHALL report `device_info` with identifier `(DOMAIN, f"{entry_id}_gas")`
- **AND** this SHALL include `gas_total_cost`
