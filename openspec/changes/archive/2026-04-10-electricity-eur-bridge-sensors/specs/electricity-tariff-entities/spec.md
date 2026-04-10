## MODIFIED Requirements

### Requirement: Electricity unit is fixed to c€/kWh
The electricity config entry SHALL NOT include a user-selectable unit field. The electricity domain SHALL always use `c€/kWh` as its unit. All electricity number entities (tariff rates and surcharge) and electricity price sensors SHALL use `c€/kWh` as their `native_unit_of_measurement`.

#### Scenario: User sets up the electricity domain
- **WHEN** a user completes the electricity config flow
- **THEN** no unit selector is shown and the config entry does not store a `unit` key
- **THEN** all electricity tariff number entities are created with `native_unit_of_measurement = "c€/kWh"`

#### Scenario: User opens electricity options
- **WHEN** a user opens the options flow for the electricity config entry
- **THEN** no unit selector is shown

#### Scenario: Existing config entry with a stored unit value
- **WHEN** an existing electricity config entry has a `unit` key in its stored data (from a prior version)
- **THEN** the `unit` value is ignored and `c€/kWh` is used for all electricity entities

## REMOVED Requirements

### Requirement: Electricity unit selector in config and options flow
**Reason**: The electricity unit is now hardcoded to `c€/kWh`. Belgian tariffs are always expressed at the centi-euro per kWh scale and offering other units only creates confusion with no valid use case.  
**Migration**: No user action required. Existing entries will silently use `c€/kWh`. Previously entered tariff values are not rescaled — they are assumed to have already been entered in `c€/kWh`.
