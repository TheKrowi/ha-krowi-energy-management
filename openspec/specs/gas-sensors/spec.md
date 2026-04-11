# Spec: gas-sensors

## Purpose

Defines the computed gas sensor entities: total surcharge rate and current gas price.

## Requirements

### Requirement: Gas total surcharge rate sensor
The component SHALL expose a sensor with unique ID `gas_tariff_total_surcharge` and English display name "Total surcharge" that reports the sum of the four gas tariff rate number entities (excluding VAT).

Formula: `distribution + transport + excise_duty + energy_contribution`

`unit_of_measurement` SHALL be `"c€/kWh"`. `state_class` SHALL be `measurement`. Value SHALL be rounded to 5 decimal places.

#### Scenario: Gas surcharge updates when any rate entity changes
- **WHEN** any of the four contributing gas tariff entities changes state
- **THEN** `gas_tariff_total_surcharge` SHALL recompute immediately
- **THEN** the new state SHALL equal the sum, rounded to 5 decimal places

#### Scenario: All gas rates zero initially
- **WHEN** no gas rate has been configured yet
- **THEN** the sensor state SHALL be `"0.00000"`

---

### Requirement: Gas current price sensor
The component SHALL expose a sensor with unique ID `gas_current_price` and English display name "Current price" that computes the current gas price.

Formula: `(spot_price + surcharge) * (1 + vat / 100)`, rounded to 5 decimal places.

Where:
- `spot_price` is the state of `gas_spot_today_price` (always `c€/kWh`)
- `surcharge` is the state of `gas_tariff_total_surcharge` (always `c€/kWh`)
- `vat` is the state of `gas_vat` (in %)

`unit_of_measurement` SHALL be `"c€/kWh"`. `state_class` SHALL be `measurement`.

The sensor SHALL track state changes on `gas_spot_today_price`, `gas_tariff_total_surcharge`, and `gas_vat`.

#### Scenario: Gas price computed correctly
- **WHEN** `gas_spot_today_price` is `4.543` (c€/kWh), gas surcharge is `0.55` (c€/kWh), VAT is `21.0%`
- **THEN** gas price SHALL be `(4.543 + 0.55) * 1.21 = 6.16253` (rounded to 5 decimal places)

#### Scenario: Gas price is unavailable when spot price is unavailable
- **WHEN** `gas_spot_today_price` is `unavailable` or `unknown`
- **THEN** `gas_current_price` state SHALL be `unavailable`

#### Scenario: Gas price updates when spot price changes
- **WHEN** `gas_spot_today_price` changes after a daily store refresh
- **THEN** `gas_current_price` SHALL recompute immediately

---

### Requirement: Gas sensors grouped under Gas device
All gas sensor entities SHALL return a `DeviceInfo` that places them under the shared Gas device.

The device identifier SHALL be `(DOMAIN, f"{entry_id}_gas")`.

All gas sensor entities (`gas_tariff_total_surcharge`, `gas_tariff_total_surcharge_formula`, `gas_current_price`, `gas_current_price_eur`, `gas_spot_today_price`, `gas_spot_average_price`, `gas_calorific_value`, `gas_current_price_m3`, `gas_consumption_kwh`, `gas_total_cost`) SHALL be associated with this device.

#### Scenario: Gas sensors grouped under Gas device
- **WHEN** the gas config entry is set up
- **THEN** all gas sensor entities SHALL report `device_info` with identifier `(DOMAIN, f"{entry_id}_gas")`
- **AND** this SHALL include `gas_total_cost`
