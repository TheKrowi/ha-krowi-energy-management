# Spec: Entity ID Stability

## Purpose

Entity IDs in the `krowi_energy_management` integration must be stable and predictable, independent of display names or naming conventions. This ensures automations, dashboards, and scripts that reference entity IDs continue to work across updates.

## Requirements

### Requirement: Entity IDs are pinned to UID constants
Every entity in the `krowi_energy_management` integration SHALL have its `entity_id` explicitly set to `<platform>.<uid_suffix>`, where `<uid_suffix>` is the corresponding `UID_*` constant value from `const.py`. Entity IDs SHALL NOT be derived from `_attr_name`.

#### Scenario: Number entity ID matches UID constant
- **WHEN** a number entity is registered with `unique_id_suffix = "electricity_vat_rate"`
- **THEN** its `entity_id` SHALL be `number.electricity_vat_rate`

#### Scenario: Sensor entity ID matches UID constant
- **WHEN** a sensor entity is registered with unique ID suffix `"electricity_price_import"`
- **THEN** its `entity_id` SHALL be `sensor.electricity_price_import`

#### Scenario: Dutch display name does not alter entity ID
- **WHEN** a number entity has `_attr_name = "BTW elektriciteit"` and `unique_id_suffix = "electricity_vat_rate"`
- **THEN** its `entity_id` SHALL still be `number.electricity_vat_rate`

#### Scenario: English display name with different word order does not alter entity ID
- **WHEN** a sensor entity has `_attr_name = "Electricity import price"` and its UID constant is `"electricity_price_import"`
- **THEN** its `entity_id` SHALL be `sensor.electricity_price_import`
