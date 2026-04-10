## MODIFIED Requirements

### Requirement: Five gas tariff number entities are created
The component SHALL create five `NumberEntity` instances for gas tariffs when the gas config entry is loaded.

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
- **WHEN** the gas config entry is loaded
- **THEN** all five gas number entities SHALL exist in HA with the correct entity IDs derived from the UIDs above

#### Scenario: All gas tariff number entities use c€/kWh
- **WHEN** the gas config entry is loaded
- **THEN** `gas_tariff_distribution`, `gas_tariff_transport`, `gas_tariff_excise_duty`, and `gas_tariff_energy_contribution` SHALL each have `unit_of_measurement = "c€/kWh"`
- **THEN** `gas_vat` SHALL have `unit_of_measurement = "%"`

## REMOVED Requirements

### Requirement: Gas unit selector in config entry
**Reason**: Gas unit is now hardcoded to `c€/kWh`. The `unit` field has been removed from the gas config entry data shape. The `gas_unit` variable is replaced by the `GAS_UNIT = "c€/kWh"` constant throughout.
**Migration**: Existing v2 gas config entries with a `unit` field will have it stripped by the v2 → v3 migration.
