# Spec: gas-tariff-entities

## Purpose

Defines the gas tariff number entities, their unit configuration, persistence, and device grouping.

## Requirements

### Requirement: Five gas tariff number entities are created
The component SHALL create five `NumberEntity` instances for gas tariffs when the config entry is loaded.

Entities (all under domain `krowi_energy_management`):

| Unique ID | Friendly name (EN) | Unit | Min | Max | Step |
|-----------|-------------------|------|-----|-----|------|
| `gas_tariff_distribution` | Distribution | `c€/kWh` | 0 | 9999 | 0.00001 |
| `gas_tariff_transport` | Transport (Fluxys) | `c€/kWh` | 0 | 9999 | 0.00001 |
| `gas_tariff_excise_duty` | Excise duty | `c€/kWh` | 0 | 9999 | 0.00001 |
| `gas_tariff_energy_contribution` | Energy contribution | `c€/kWh` | 0 | 9999 | 0.00001 |
| `gas_vat` | VAT | `%` | 0 | 100 | 0.01 |

Gas unit is permanently `c€/kWh` (defined by the `GAS_UNIT` constant). It is no longer read from the config entry.

#### Scenario: Entities are present after setup
- **WHEN** the config entry is loaded
- **THEN** all five gas number entities SHALL exist in HA with the correct entity IDs derived from the UIDs above

#### Scenario: VAT entity has percent unit regardless of gas_unit
- **WHEN** gas_unit is `c€/kWh`
- **THEN** `gas_vat` SHALL have `unit_of_measurement = "%"`
- **THEN** all other gas tariff entities SHALL have `unit_of_measurement = "c€/kWh"`

---

### Requirement: Gas tariff values are editable and persisted
Users SHALL be able to set gas tariff values via the HA UI or the `number.set_value` service call. Values SHALL survive HA restarts.

#### Scenario: Value set via HA service
- **WHEN** `number.set_value` is called with a valid value for a gas tariff entity
- **THEN** the entity state SHALL immediately reflect the new value
- **THEN** gas sensors that depend on this entity SHALL recompute reactively

#### Scenario: Value survives restart
- **WHEN** HA restarts after a value was set
- **THEN** the entity SHALL restore its previous value via `RestoreNumber`

#### Scenario: Initial value on first creation
- **WHEN** a gas tariff entity is created for the first time with no restore state available
- **THEN** its native value SHALL be `0`

---

### Requirement: Gas number entity mode is box
All gas tariff number entities SHALL use `mode = "box"`.

#### Scenario: Mode attribute is box
- **WHEN** the entity state is read via the HA REST API
- **THEN** the `mode` attribute SHALL be `"box"`

---

### Requirement: Gas entities grouped under Gas device
All gas number entities SHALL return a `DeviceInfo` that places them under a shared Gas device, grouped under the `krowi_energy_management` integration.

The device identifier SHALL be `(DOMAIN, f"{entry_id}_gas")`.

#### Scenario: Gas number entities belong to Gas device
- **WHEN** the component is loaded
- **THEN** all five gas number entities SHALL be associated with the device identified by `(DOMAIN, entry_id + "_gas")`
- **THEN** this device SHALL appear under the Krowi Energy Management integration in the HA devices panel
