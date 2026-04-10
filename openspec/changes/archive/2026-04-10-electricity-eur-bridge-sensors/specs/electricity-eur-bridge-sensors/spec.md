## ADDED Requirements

### Requirement: Import price EUR bridge sensor
The component SHALL expose a sensor with unique ID `electricity_price_import_eur` and `native_unit_of_measurement = "EUR/kWh"`. Its value SHALL equal the state of `electricity_price_import` divided by 100, rounded to 5 decimal places. The sensor SHALL belong to the Electricity device for its config entry.

#### Scenario: Source sensor has a numeric state
- **WHEN** `electricity_price_import` emits a state change with a parseable float value
- **THEN** `electricity_price_import_eur` updates its state to that value ÷ 100, rounded to 5 decimal places

#### Scenario: Source sensor is unavailable or non-numeric
- **WHEN** `electricity_price_import` emits a state that is not a parseable float (e.g. `unavailable`, `unknown`)
- **THEN** `electricity_price_import_eur` sets its state to `None` (rendered as `unavailable` by HA)

#### Scenario: Initial state on startup
- **WHEN** the sensor is added to HA and before any state change event fires
- **THEN** `electricity_price_import_eur` performs an initial update by reading the current state of `electricity_price_import`, applying the ÷ 100 conversion, and writing the result (or `None` if unavailable)

### Requirement: Export price EUR bridge sensor
The component SHALL expose a sensor with unique ID `electricity_price_export_eur` and `native_unit_of_measurement = "EUR/kWh"`. Its value SHALL equal the state of `electricity_price_export` divided by 100, rounded to 5 decimal places. The sensor SHALL belong to the Electricity device for its config entry.

#### Scenario: Source sensor has a numeric state
- **WHEN** `electricity_price_export` emits a state change with a parseable float value
- **THEN** `electricity_price_export_eur` updates its state to that value ÷ 100, rounded to 5 decimal places

#### Scenario: Source sensor is unavailable or non-numeric
- **WHEN** `electricity_price_export` emits a state that is not a parseable float
- **THEN** `electricity_price_export_eur` sets its state to `None`

#### Scenario: Initial state on startup
- **WHEN** the sensor is added to HA and before any state change event fires
- **THEN** `electricity_price_export_eur` performs an initial update by reading the current state of `electricity_price_export`, applying the ÷ 100 conversion, and writing the result (or `None` if unavailable)

### Requirement: Bridge sensors are reactive
The bridge sensors SHALL use `async_track_state_change_event` to listen for state changes on the source sensors. They SHALL NOT poll.

#### Scenario: Source sensor changes value
- **WHEN** the source sensor (`electricity_price_import` or `electricity_price_export`) emits a state change event
- **THEN** the corresponding bridge sensor immediately updates and writes its new state to HA

### Requirement: Bridge sensors expose EUR/kWh unit for HA Energy Dashboard
The bridge sensors SHALL use `native_unit_of_measurement = "EUR/kWh"` so that the HA Energy Dashboard can accept them as electricity price sources.

#### Scenario: User attempts to link bridge sensor to Energy Dashboard
- **WHEN** the user opens the HA Energy Dashboard configuration
- **THEN** `electricity_price_import_eur` and `electricity_price_export_eur` are available as selectable cost sensors
