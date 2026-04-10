## ADDED Requirements

### Requirement: Settings config entry registers no platform entities
The settings config entry SHALL NOT be forwarded to the `number` or `sensor` platforms. `async_setup_entry` in `__init__.py` SHALL only call `async_forward_entry_setups` when `domain_type` is `"electricity"` or `"gas"`. The settings entry is a configuration-only entry.

#### Scenario: Settings entry produces no number entities
- **WHEN** a settings config entry is loaded
- **THEN** no `NumberEntity` objects SHALL be registered in the HA entity registry under this entry

#### Scenario: Settings entry produces no sensor entities
- **WHEN** a settings config entry is loaded
- **THEN** no `SensorEntity` objects SHALL be registered in the HA entity registry under this entry

#### Scenario: Gas entry is unaffected by the guard
- **WHEN** a gas config entry is loaded
- **THEN** gas tariff `NumberEntity` objects SHALL be registered as normal
- **THEN** gas `SensorEntity` objects SHALL be registered as normal

#### Scenario: Electricity entry is unaffected by the guard
- **WHEN** an electricity config entry is loaded
- **THEN** electricity tariff `NumberEntity` objects SHALL be registered as normal
- **THEN** electricity `SensorEntity` objects SHALL be registered as normal

### Requirement: Platform setup functions have explicit domain-type guards
`number.async_setup_entry` and `sensor.async_setup_entry` SHALL use explicit `if/elif` branches for `electricity` and `gas`, and SHALL return early (no-op) for any other `domain_type`. Implicit fall-through to gas descriptors is not allowed.

#### Scenario: Unknown domain type in number platform produces no entities
- **WHEN** `number.async_setup_entry` is called with a `domain_type` that is neither `"electricity"` nor `"gas"`
- **THEN** no entities SHALL be added and the function SHALL return without error

#### Scenario: Unknown domain type in sensor platform produces no entities
- **WHEN** `sensor.async_setup_entry` is called with a `domain_type` that is neither `"electricity"` nor `"gas"`
- **THEN** no entities SHALL be added and the function SHALL return without error
