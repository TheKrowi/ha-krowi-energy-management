## MODIFIED Requirements

### Requirement: Import price EUR bridge sensor
The component SHALL expose a sensor with unique ID `electricity_current_price_import_eur` and English display name "Current import price (EUR/kWh)" and `native_unit_of_measurement = "EUR/kWh"`. Its value SHALL equal the state of `electricity_current_price_import` divided by 100, rounded to 5 decimal places. The sensor SHALL belong to the Electricity device for its config entry.

#### Scenario: Source sensor has a numeric state
- **WHEN** `electricity_current_price_import` emits a state change with a parseable float value
- **THEN** `electricity_current_price_import_eur` updates its state to that value ÷ 100, rounded to 5 decimal places

#### Scenario: Source sensor is unavailable or non-numeric
- **WHEN** `electricity_current_price_import` emits a state that is not a parseable float (e.g. `unavailable`, `unknown`)
- **THEN** `electricity_current_price_import_eur` sets its state to `None` (rendered as `unavailable` by HA)

#### Scenario: Initial state on startup
- **WHEN** the sensor is added to HA and before any state change event fires
- **THEN** `electricity_current_price_import_eur` performs an initial update by reading the current state of `electricity_current_price_import`, applying the ÷ 100 conversion, and writing the result (or `None` if unavailable)

### Requirement: Export price EUR bridge sensor
The component SHALL expose a sensor with unique ID `electricity_current_price_export_eur` and English display name "Current export price (EUR/kWh)" and `native_unit_of_measurement = "EUR/kWh"`. Its value SHALL equal the state of `electricity_current_price_export` divided by 100, rounded to 5 decimal places. The sensor SHALL belong to the Electricity device for its config entry.

#### Scenario: Source sensor has a numeric state
- **WHEN** `electricity_current_price_export` emits a state change with a parseable float value
- **THEN** `electricity_current_price_export_eur` updates its state to that value ÷ 100, rounded to 5 decimal places

#### Scenario: Source sensor is unavailable or non-numeric
- **WHEN** `electricity_current_price_export` emits a state that is not a parseable float
- **THEN** `electricity_current_price_export_eur` sets its state to `None`

#### Scenario: Initial state on startup
- **WHEN** the sensor is added to HA and before any state change event fires
- **THEN** `electricity_current_price_export_eur` performs an initial update by reading the current state of `electricity_current_price_export`, applying the ÷ 100 conversion, and writing the result (or `None` if unavailable)
