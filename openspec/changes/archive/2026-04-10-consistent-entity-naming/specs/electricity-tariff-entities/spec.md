## MODIFIED Requirements

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
