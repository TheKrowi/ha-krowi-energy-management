# Spec: electricity-sensors

## Purpose

Defines the computed electricity sensor entities: total surcharge rate, surcharge formula string, import price, and export price.

## Requirements

### Requirement: Electricity total surcharge rate sensor
The component SHALL expose a sensor with unique ID `electricity_tariff_total_surcharge` and English display name "Total surcharge" that reports the sum of the four electricity tariff rate number entities (excluding VAT).

Formula: `green_energy_contribution + distribution_transport + excise_duty + energy_contribution`

The sensor's `unit_of_measurement` SHALL match `electricity_unit`. `state_class` SHALL be `measurement`. Value SHALL be rounded to 5 decimal places.

#### Scenario: Surcharge updates when any rate entity changes
- **WHEN** any of the four contributing electricity tariff entities changes state
- **THEN** `electricity_tariff_total_surcharge` SHALL recompute immediately
- **THEN** the new state SHALL equal the sum of the four rates, rounded to 5 decimal places

#### Scenario: All rates are zero initially
- **WHEN** no rate has been configured yet (all at initial value 0)
- **THEN** the sensor state SHALL be `"0.00000"`

---

### Requirement: Electricity surcharge formula string sensor
The component SHALL expose a sensor with unique ID `electricity_tariff_total_surcharge_formula` and English display name "Total surcharge formula" that renders the surcharge calculation as a human-readable string.

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
The component SHALL expose a sensor with unique ID `electricity_current_price_import` and English display name "Current import price" that computes the current electricity import price.

Formula: `(spot_price + surcharge) * (1 + vat / 100)`, rounded to 5 decimal places.

Where:
- `spot_price` is the state of `electricity_spot_current_price` (always `c€/kWh`)
- `surcharge` is the state of `electricity_tariff_total_surcharge` (always `c€/kWh`)
- `vat` is the state of `electricity_vat` (in %)

`unit_of_measurement` SHALL be `"c€/kWh"`. `state_class` SHALL be `measurement`.

The sensor SHALL track state changes on `electricity_spot_current_price`, `electricity_tariff_total_surcharge`, and `electricity_vat`.

#### Scenario: Import price computed correctly
- **WHEN** `electricity_spot_current_price` is `9.079` (c€/kWh), surcharge is `5.442` (c€/kWh), VAT is `21.0%`
- **THEN** import price SHALL be `(9.079 + 5.442) * 1.21 = 17.57002` (rounded to 5 decimal places)

#### Scenario: Import price is unavailable when spot price is unavailable
- **WHEN** `electricity_spot_current_price` is `unavailable` or `unknown`
- **THEN** `electricity_current_price_import` state SHALL be `unavailable`

#### Scenario: Import price updates when spot price changes
- **WHEN** `electricity_spot_current_price` changes to a new value on a 15-min tick
- **THEN** `electricity_current_price_import` SHALL recompute immediately

---

### Requirement: Electricity export price sensor (reactive Jinja2 template)
The component SHALL expose a sensor with unique ID `electricity_current_price_export` and English display name "Current export price" that renders the user-supplied Jinja2 `export_template` from the config entry.

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
