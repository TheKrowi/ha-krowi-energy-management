## MODIFIED Requirements

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

Gas unit is permanently `c€/kWh` (defined by the `GAS_UNIT` constant). It is not read from the config entry.

#### Scenario: Entities are present after setup
- **WHEN** the config entry is loaded
- **THEN** all five gas number entities SHALL exist in HA with the correct entity IDs derived from the UIDs above

#### Scenario: VAT entity has percent unit regardless of gas_unit
- **WHEN** gas_unit is `c€/kWh`
- **THEN** `gas_vat` SHALL have `unit_of_measurement = "%"`
- **THEN** all other gas tariff entities SHALL have `unit_of_measurement = "c€/kWh"`

## ADDED Requirements

### Requirement: Gas options flow exposes GOS zone selector
The gas options flow SHALL include a selector for `CONF_GOS_ZONE` rendered as a dropdown containing all Belgian GOS zone names from the current Atrias GCV file. The default value SHALL be `"GOS FLUVIUS - LEUVEN"`.

The zone list SHALL be a hardcoded constant `GOS_ZONE_OPTIONS` in `const.py` derived from the known Atrias zone names. It SHALL be presented alphabetically.

#### Scenario: GOS zone default is pre-selected
- **WHEN** the gas options flow is opened for the first time
- **THEN** `CONF_GOS_ZONE` SHALL default to `"GOS FLUVIUS - LEUVEN"`

#### Scenario: User can change GOS zone
- **WHEN** the user selects a different zone in the options flow and saves
- **THEN** `CONF_GOS_ZONE` SHALL be updated in `entry.options`
- **THEN** `GcvStore` SHALL use the new zone on the next fetch

---

### Requirement: Gas options flow exposes gas meter entity selector
The gas options flow SHALL include an `EntitySelector()` field for `CONF_GAS_METER_ENTITY`. The default value SHALL be `"sensor.gas_meter_consumption"`.

#### Scenario: Default gas meter entity pre-populated
- **WHEN** the gas options flow is opened for the first time
- **THEN** `CONF_GAS_METER_ENTITY` SHALL default to `"sensor.gas_meter_consumption"`

#### Scenario: User can clear gas meter entity
- **WHEN** the user clears `CONF_GAS_METER_ENTITY` and saves
- **THEN** the field SHALL be stored as `None`
- **THEN** `gas_consumption_kwh` state SHALL become `unavailable`
