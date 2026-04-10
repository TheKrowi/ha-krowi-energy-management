# Spec: electricity-tariff-entities

## Purpose

Defines the electricity tariff number entities and their unit configuration. The electricity domain always uses `c€/kWh` as its fixed unit.

## Requirements

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

---

### Requirement: Five electricity tariff number entities are created
The component SHALL create five `NumberEntity` instances for electricity tariffs when the config entry is loaded.

Entities (all under domain `krowi_energy_management`):

| Unique ID | Friendly name (EN) | Unit | Min | Max | Step |
|-----------|-------------------|------|-----|-----|------|
| `electricity_tariff_green_energy_contribution` | Green energy contribution | electricity_unit | 0 | 9999 | 0.00001 |
| `electricity_tariff_distribution_transport` | Distribution & transport | electricity_unit | 0 | 9999 | 0.00001 |
| `electricity_tariff_excise_duty` | Excise duty | electricity_unit | 0 | 9999 | 0.00001 |
| `electricity_tariff_energy_contribution` | Energy contribution | electricity_unit | 0 | 9999 | 0.00001 |
| `electricity_vat` | VAT | `%` | 0 | 100 | 0.01 |

`electricity_unit` is always `c€/kWh` for the electricity domain.

#### Scenario: Entities are present after setup
- **WHEN** the config entry is loaded
- **THEN** all five electricity number entities SHALL exist in HA with the correct entity IDs derived from the UIDs above

#### Scenario: VAT entity has percent unit regardless of electricity_unit
- **WHEN** the electricity entry is loaded
- **THEN** `electricity_vat` SHALL have `unit_of_measurement = "%"`
- **THEN** all other electricity tariff entities SHALL have `unit_of_measurement = "c€/kWh"`

---

### Requirement: Electricity tariff values are editable and persisted
Users SHALL be able to set tariff values via the HA UI or the `number.set_value` service call. Values SHALL survive HA restarts.

#### Scenario: Value set via HA service
- **WHEN** `number.set_value` is called with a valid value for an electricity tariff entity
- **THEN** the entity state SHALL immediately reflect the new value
- **THEN** all electricity sensors that depend on this entity SHALL recompute reactively

#### Scenario: Value survives restart
- **WHEN** HA restarts after a value was set
- **THEN** the entity SHALL restore its previous value via `RestoreNumber`

#### Scenario: Initial value on first creation
- **WHEN** an electricity tariff entity is created for the first time with no restore state available
- **THEN** its native value SHALL be `0`

---

### Requirement: Number entity mode is box
All electricity tariff number entities SHALL use `mode = "box"` (direct text input in HA UI).

#### Scenario: Mode attribute is box
- **WHEN** the entity state is read via the HA REST API
- **THEN** the `mode` attribute SHALL be `"box"`

---

### Requirement: Electricity entities grouped under Electricity device
All electricity number entities SHALL return a `DeviceInfo` that places them under a shared Electricity device, grouped under the `krowi_energy_management` integration.

The device identifier SHALL be `(DOMAIN, f"{entry_id}_electricity")`.

#### Scenario: Electricity number entities belong to Electricity device
- **WHEN** the component is loaded
- **THEN** all five electricity number entities SHALL be associated with the device identified by `(DOMAIN, entry_id + "_electricity")`
- **THEN** this device SHALL appear under the Krowi Energy Management integration in the HA devices panel
