## MODIFIED Requirements

### Requirement: Five gas tariff number entities are created
The component SHALL create five `NumberEntity` instances for gas tariffs when the config entry is loaded.

Entities (all under domain `krowi_energy_management`):

| Unique ID | Friendly name (EN) | Unit | Min | Max | Step |
|-----------|-------------------|------|-----|-----|------|
| `gas_tariff_distribution` | Distribution | gas_unit | 0 | 9999 | 0.00001 |
| `gas_tariff_transport` | Transport (Fluxys) | gas_unit | 0 | 9999 | 0.00001 |
| `gas_tariff_excise_duty` | Excise duty | gas_unit | 0 | 9999 | 0.00001 |
| `gas_tariff_energy_contribution` | Energy contribution | gas_unit | 0 | 9999 | 0.00001 |
| `gas_vat` | VAT | `%` | 0 | 100 | 0.01 |

`gas_unit` is the unit configured in the config entry (one of `c€/kWh`, `€/kWh`, `€/MWh`), independent of `electricity_unit`.

#### Scenario: Entities are present after setup
- **WHEN** the config entry is loaded
- **THEN** all five gas number entities SHALL exist in HA with the correct entity IDs derived from the UIDs above

#### Scenario: VAT entity has percent unit regardless of gas_unit
- **WHEN** gas_unit is `c€/kWh`
- **THEN** `gas_vat` SHALL have `unit_of_measurement = "%"`
- **THEN** all other gas tariff entities SHALL have `unit_of_measurement = "c€/kWh"`
