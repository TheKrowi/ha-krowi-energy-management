# Spec: gas-sensors

## Purpose

Defines the computed gas sensor entities: total surcharge rate and current gas price.

## Requirements

### Requirement: Gas total surcharge rate sensor
The component SHALL expose a sensor `gas_surcharge_rate` that reports the sum of the four gas rate number entities (excluding VAT).

Formula: `distribution + transport + excise_duty + energy_contribution`

`unit_of_measurement` SHALL equal `gas_unit`. `state_class` SHALL be `measurement`. Value SHALL be rounded to 5 decimal places.

#### Scenario: Gas surcharge updates when any rate entity changes
- **WHEN** any of the four contributing gas rate entities changes state
- **THEN** `gas_surcharge_rate` SHALL recompute immediately
- **THEN** the new state SHALL equal the sum, rounded to 5 decimal places

#### Scenario: All gas rates zero initially
- **WHEN** no gas rate has been configured yet
- **THEN** the sensor state SHALL be `"0.00000"`

---

### Requirement: Gas current price sensor
The component SHALL expose a sensor `gas_price` that computes the current gas price.

Formula: `(current_price + surcharge) * (1 + vat / 100)`, rounded to 5 decimal places.

Where:
- `current_price` is the state of the configured `current_price_entity`, read dynamically and auto-converted to `gas_unit` based on the entity's `unit_of_measurement` attribute
- `surcharge` is the state of `gas_surcharge_rate`
- `vat` is the state of `gas_vat_rate` (in %)

`unit_of_measurement` SHALL equal `gas_unit`. `state_class` SHALL be `measurement`.

#### Scenario: Gas price computed correctly
- **WHEN** TTF DAM reports `52.90` €/MWh, `gas_unit` is `€/MWh`, gas surcharge is `5.50` €/MWh, VAT is `21.0%`
- **THEN** gas price SHALL be `(52.90 + 5.50) * 1.21 = 70.664` rounded to 5 decimal places = `"70.66400"`

#### Scenario: Current price entity auto-converted from MWh to kWh
- **WHEN** `current_price_entity` reports in `€/MWh` and `gas_unit` is `€/kWh`
- **THEN** the source value SHALL be divided by `1000` before applying the formula

#### Scenario: Current price entity auto-converted from kWh to MWh
- **WHEN** `current_price_entity` reports in `€/kWh` and `gas_unit` is `€/MWh`
- **THEN** the source value SHALL be multiplied by `1000` before applying the formula

#### Scenario: Gas price is unavailable when current price entity is unavailable
- **WHEN** the configured `current_price_entity` is missing or `unavailable`/`unknown`
- **THEN** `gas_price` state SHALL be `unavailable`

#### Scenario: Current price entity unit not recognised
- **WHEN** the `current_price_entity`'s `unit_of_measurement` attribute cannot be matched to a known unit
- **THEN** `gas_price` SHALL be set to `unavailable`
- **THEN** a warning SHALL be logged indicating the unrecognised unit

---

### Requirement: Gas sensors grouped under Gas device
All gas sensor entities SHALL return a `DeviceInfo` that places them under the shared Gas device.

The device identifier SHALL be `(DOMAIN, f"{entry_id}_gas")`.

#### Scenario: Gas sensors belong to Gas device
- **WHEN** the component is loaded
- **THEN** all two gas sensor entities SHALL be associated with the device identified by `(DOMAIN, entry_id + "_gas")`
