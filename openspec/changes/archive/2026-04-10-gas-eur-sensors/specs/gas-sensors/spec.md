## MODIFIED Requirements

### Requirement: Gas sensors grouped under Gas device
All gas sensor entities SHALL return a `DeviceInfo` that places them under the shared Gas device.

The device identifier SHALL be `(DOMAIN, f"{entry_id}_gas")`.

All **four** gas sensor entities (`gas_tariff_total_surcharge`, `gas_tariff_total_surcharge_formula`, `gas_current_price`, `gas_current_price_eur`) SHALL be associated with this device.

#### Scenario: Gas sensors belong to Gas device
- **WHEN** the component is loaded
- **THEN** all four gas sensor entities SHALL be associated with the device identified by `(DOMAIN, entry_id + "_gas")`
