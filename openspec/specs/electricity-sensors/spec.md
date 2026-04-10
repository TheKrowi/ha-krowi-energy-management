# Spec: electricity-sensors

## Purpose

Defines the computed electricity sensor entities: total surcharge rate, surcharge formula string, import price, and export price.

## Requirements

### Requirement: Electricity total surcharge rate sensor
The component SHALL expose a sensor `electricity_surcharge_rate` that reports the sum of the four electricity rate number entities (excluding VAT).

Formula: `green_energy + distribution_transport + excise_duty + energy_contribution`

The sensor's `unit_of_measurement` SHALL match `electricity_unit`. `state_class` SHALL be `measurement`. Value SHALL be rounded to 5 decimal places.

#### Scenario: Surcharge updates when any rate entity changes
- **WHEN** any of the four contributing electricity rate entities changes state
- **THEN** `electricity_surcharge_rate` SHALL recompute immediately
- **THEN** the new state SHALL equal the sum of the four rates, rounded to 5 decimal places

#### Scenario: All rates are zero initially
- **WHEN** no rate has been configured yet (all at initial value 0)
- **THEN** the sensor state SHALL be `"0.00000"`

---

### Requirement: Electricity surcharge formula string sensor
The component SHALL expose a sensor `electricity_surcharge_formula` that renders the surcharge calculation as a human-readable string.

Format: `"<r1> + <r2> + <r3> + <r4> = <total>"` where each value is rounded to 5 decimal places.

This sensor has no `unit_of_measurement` and no `state_class`.

#### Scenario: Formula string reflects current rate values
- **WHEN** the rates are `0.01250`, `0.03750`, `0.00422`, `0.00020`
- **THEN** the sensor state SHALL be `"0.01250 + 0.03750 + 0.00422 + 0.00020 = 0.05442"`

#### Scenario: Formula updates when any rate changes
- **WHEN** any contributing electricity rate entity changes
- **THEN** the formula string sensor SHALL recompute immediately

---

### Requirement: Electricity import price sensor
The component SHALL expose a sensor `electricity_price_import` that computes the current electricity import price.

Formula: `(current_price + surcharge) * (1 + vat / 100)`, rounded to 5 decimal places.

Where:
- `current_price` is the state of the configured `current_price_entity`, auto-converted to `electricity_unit`
- `surcharge` is the state of `electricity_surcharge_rate`
- `vat` is the state of `electricity_vat_rate` (in %)

`unit_of_measurement` SHALL equal `electricity_unit`. `state_class` SHALL be `measurement`.

#### Scenario: Import price computed correctly
- **WHEN** Nord Pool reports `0.09079` €/kWh, surcharge is `0.05442` €/kWh, VAT is `21.0%`
- **THEN** import price SHALL be `(0.09079 + 0.05442) * 1.21 = 0.17570` (rounded to 5 decimal places)

#### Scenario: Nord Pool unit auto-converted from MWh to kWh
- **WHEN** Nord Pool entity reports in `€/MWh` and `electricity_unit` is `€/kWh`
- **THEN** Nord Pool value SHALL be divided by `1000` before applying the formula

#### Scenario: FX conversion applied when configured
- **WHEN** `fx_rate_entity` is set and its state is `0.086` (e.g. NOK/EUR)
- **WHEN** the configured `current_price_entity` reports in `NOK/kWh` and `electricity_unit` is `€/kWh`
- **THEN** the source value SHALL first be magnitude-converted (factor = 1.0, same magnitude), then multiplied by `0.086`
- **THEN** the result SHALL equal `source_nok_value * 0.086`

#### Scenario: Import price is unavailable when current price entity is unavailable
- **WHEN** the configured `current_price_entity` is missing or in `unavailable`/`unknown` state
- **THEN** `electricity_price_import` state SHALL be `unavailable`

#### Scenario: Import price is unavailable when FX sensor is unavailable
- **WHEN** `fx_rate_entity` is configured but the entity is `unavailable` or non-numeric
- **THEN** `electricity_price_import` state SHALL be `unavailable`

#### Scenario: Unit not recognised
- **WHEN** the `current_price_entity`'s `unit_of_measurement` attribute cannot be mapped to a known unit
- **THEN** `electricity_price_import` SHALL be set to `unavailable`
- **THEN** a warning SHALL be logged indicating the unrecognised unit

---

### Requirement: Electricity export price sensor (reactive Jinja2 template)
The component SHALL expose a sensor `electricity_price_export` that renders the user-supplied Jinja2 `export_template` from the config entry.

The sensor SHALL use HA's `async_track_template_result` so it updates reactively whenever any entity referenced in the template changes state.

`unit_of_measurement` SHALL equal `electricity_unit`. `state_class` SHALL be `measurement`.

#### Scenario: Export price renders correctly
- **WHEN** the template is `{{ (states('sensor.nord_pool_be_average_price') | float(0) * 0.94 - 0.017) | round(5) }}`
- **WHEN** `sensor.nord_pool_be_average_price` state is `0.10000`
- **THEN** export price state SHALL be `"0.07700"`

#### Scenario: Export price updates when referenced entity changes
- **WHEN** any entity referenced in the template changes state
- **THEN** the export price sensor SHALL rerender and update its state

#### Scenario: Export price is unavailable on template error
- **WHEN** the template raises a rendering error (e.g. syntax error or division by zero)
- **THEN** the sensor state SHALL be `unavailable`
- **THEN** the error SHALL be logged

---

### Requirement: Electricity sensors grouped under Electricity device
All electricity sensor entities SHALL return a `DeviceInfo` that places them under the shared Electricity device.

The device identifier SHALL be `(DOMAIN, f"{entry_id}_electricity")`.

#### Scenario: Electricity sensors belong to Electricity device
- **WHEN** the component is loaded
- **THEN** all four electricity sensor entities SHALL be associated with the device identified by `(DOMAIN, entry_id + "_electricity")`
