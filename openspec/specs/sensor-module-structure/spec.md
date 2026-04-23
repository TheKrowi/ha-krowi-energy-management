### Requirement: Sensor platform is split into domain-specific modules

The sensor platform SHALL be organised across the following files:

| File | Contents |
|------|----------|
| `sensor.py` | HA platform entrypoint only — `async_setup_entry` routing |
| `sensor_base.py` | `KrowiSensor` base class and `_resolve_entity_id` helper |
| `sensor_electricity.py` | All electricity-domain sensor classes + `async_setup` function |
| `sensor_gas.py` | All gas-domain sensor classes + `async_setup` function |
| `sensor_supplier.py` | All supplier-domain sensor classes + `async_setup` function |

`sensor.py` SHALL contain no sensor entity class definitions.

`sensor_base.py` SHALL contain `KrowiSensor` and `_resolve_entity_id` and no domain-specific sensor classes.

Domain modules (`sensor_electricity.py`, `sensor_gas.py`, `sensor_supplier.py`) SHALL NOT import from each other.

#### Scenario: HA loads electricity entry
- **WHEN** a config entry with `domain_type = "electricity"` is loaded
- **THEN** `async_setup_entry` in `sensor.py` SHALL delegate to `sensor_electricity.async_setup`
- **THEN** all electricity sensor entities SHALL be registered successfully

#### Scenario: HA loads gas entry
- **WHEN** a config entry with `domain_type = "gas"` is loaded
- **THEN** `async_setup_entry` in `sensor.py` SHALL delegate to `sensor_gas.async_setup`
- **THEN** all gas sensor entities SHALL be registered successfully

#### Scenario: HA loads supplier entry
- **WHEN** a config entry with `domain_type = "electricity_supplier"` is loaded
- **THEN** `async_setup_entry` in `sensor.py` SHALL delegate to `sensor_supplier.async_setup`
- **THEN** all supplier sensor entities SHALL be registered successfully

### Requirement: No entity behavior changes

All entity unique IDs, entity IDs, state values, units of measurement, state classes, device classes, and `extra_state_attributes` SHALL be identical before and after this refactor.

All dispatcher signal subscriptions and state-change listener registrations SHALL behave identically before and after this refactor.

#### Scenario: Electricity entity IDs unchanged after split
- **WHEN** the split is applied
- **THEN** `sensor.electricity_spot_current_price` SHALL retain unique ID `electricity_spot_current_price`
- **THEN** all other electricity entity IDs and unique IDs SHALL be unchanged

#### Scenario: Gas entity IDs unchanged after split
- **WHEN** the split is applied
- **THEN** `sensor.gas_spot_today_price` SHALL retain unique ID `gas_spot_today_price`
- **THEN** all other gas entity IDs and unique IDs SHALL be unchanged

#### Scenario: Supplier entity IDs unchanged after split
- **WHEN** the split is applied
- **THEN** `sensor.electricity_mega_import_price` SHALL retain unique ID `electricity_mega_import_price`
- **THEN** all other supplier entity IDs and unique IDs SHALL be unchanged
