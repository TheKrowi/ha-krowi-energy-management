## ADDED Requirements

### Requirement: Electricity options flow includes eight meter and price entity selectors
The electricity options flow SHALL include eight additional `vol.Optional` `EntitySelector` fields for configuring the P1 meter entities and price entities per tariff.

| Config key | Default value |
|------------|--------------|
| `electricity_import_t1_meter_entity` | `sensor.energy_meter_energy_import_tariff_1` |
| `electricity_import_t2_meter_entity` | `sensor.energy_meter_energy_import_tariff_2` |
| `electricity_export_t1_meter_entity` | `sensor.energy_meter_energy_export_tariff_1` |
| `electricity_export_t2_meter_entity` | `sensor.energy_meter_energy_export_tariff_2` |
| `electricity_import_t1_price_entity` | `sensor.electricity_current_price_import_eur` |
| `electricity_import_t2_price_entity` | `sensor.electricity_current_price_import_eur` |
| `electricity_export_t1_price_entity` | `sensor.electricity_current_price_export_eur` |
| `electricity_export_t2_price_entity` | `sensor.electricity_current_price_export_eur` |

All eight fields SHALL use `selector.EntitySelector()` with no domain filter. All fields are optional — existing electricity config entries SHALL function without them, picking up defaults transparently.

#### Scenario: User opens electricity options for the first time
- **WHEN** a user opens the electricity options flow after this change is deployed
- **THEN** all eight fields SHALL be present, pre-filled with their default values

#### Scenario: User clears a meter entity field
- **WHEN** a user clears one of the meter entity selector fields
- **THEN** the stored value SHALL be `None`
- **THEN** the corresponding cost sensor(s) SHALL become unavailable

#### Scenario: Existing electricity entry loads without stored keys
- **WHEN** an electricity config entry from before this change is loaded
- **THEN** `async_setup_entry` SHALL use the default values for all eight missing keys
- **THEN** no migration step is required
