## ADDED Requirements

### Requirement: Multi-entry domain-based config flow with menu step
The component SHALL support multiple config entries, one per energy domain. Setup SHALL use HA's menu step to present a domain picker before domain-specific fields.

#### Scenario: User opens config flow for the first time
- **WHEN** user adds the integration
- **THEN** a menu step SHALL be shown with one button per supported domain: `Electricity` and `Gas`

#### Scenario: User selects Electricity
- **WHEN** user selects `Electricity` from the menu
- **THEN** an Electricity-specific form SHALL be shown with the fields defined in the Electricity config entry data shape
- **THEN** on submit a new config entry SHALL be created with `domain_type = "electricity"` and title `"Electricity"`

#### Scenario: User selects Gas
- **WHEN** user selects `Gas` from the menu
- **THEN** a Gas-specific form SHALL be shown with the fields defined in the Gas config entry data shape
- **THEN** on submit a new config entry SHALL be created with `domain_type = "gas"` and title `"Gas"`

---

### Requirement: Electricity config entry data shape
An electricity config entry SHALL store the following fields:

| Field | Type | Required | Default |
|---|---|---|---|
| `domain_type` | `"electricity"` | Yes | — |
| `unit` | `"c€/kWh" \| "€/kWh" \| "€/MWh"` | Yes | — |
| `current_price_entity` | string (entity ID) | Yes | `sensor.nord_pool_be_current_price` |
| `fx_rate_entity` | string (entity ID) | No | `""` (empty = no FX conversion) |
| `export_template` | string (Jinja2) | Yes | — |

#### Scenario: Electricity entry contains all fields after setup
- **WHEN** the electricity config flow step is submitted
- **THEN** the resulting config entry SHALL contain all five fields with correct types

#### Scenario: FX rate entity left empty
- **WHEN** user leaves `fx_rate_entity` blank
- **THEN** the field SHALL be stored as an empty string
- **THEN** no FX conversion SHALL be applied to the current price entity value

---

### Requirement: Gas config entry data shape
A gas config entry SHALL store the following fields:

| Field | Type | Required | Default |
|---|---|---|---|
| `domain_type` | `"gas"` | Yes | — |
| `unit` | `"c€/kWh" \| "€/kWh" \| "€/MWh"` | Yes | — |
| `current_price_entity` | string (entity ID) | Yes | `sensor.krowi_ttf_dam_30d_avg` |

#### Scenario: Gas entry contains all fields after setup
- **WHEN** the gas config flow step is submitted
- **THEN** the resulting config entry SHALL contain all three fields with correct types

---

### Requirement: Duplicate domain prevention
The config flow SHALL prevent creating a second config entry for an already-configured domain.

#### Scenario: User tries to add Electricity when it already exists
- **WHEN** an electricity config entry already exists
- **WHEN** user opens the config flow and selects `Electricity`
- **THEN** the flow SHALL abort with an `already_configured` error
- **THEN** no new config entry SHALL be created

#### Scenario: Adding Gas is allowed when only Electricity exists
- **WHEN** an electricity config entry exists but no gas entry
- **WHEN** user opens the config flow and selects `Gas`
- **THEN** the flow SHALL proceed normally and create the gas entry

---

### Requirement: Domain-aware options flow
Each config entry SHALL have an options flow that shows only the fields relevant to its domain, pre-populated with current values.

#### Scenario: Options flow for electricity entry shows only electricity fields
- **WHEN** user opens configure for the Electricity entry
- **THEN** only electricity-specific fields SHALL be shown (unit, Nord Pool entities, FX entity, export template)
- **THEN** all fields SHALL be pre-populated with the current entry values

#### Scenario: Options flow for gas entry shows only gas fields
- **WHEN** user opens configure for the Gas entry
- **THEN** only gas-specific fields SHALL be shown (unit, TTF DAM entity)
- **THEN** all fields SHALL be pre-populated with the current entry values

#### Scenario: Saving options triggers entry reload
- **WHEN** user saves the options flow for any entry
- **THEN** that entry SHALL reload completely
- **THEN** all entities belonging to that entry SHALL be re-created with the updated configuration
- **THEN** entities from other domain entries SHALL NOT be affected

---

### Requirement: User-customised entity IDs are preserved across options flow saves
Stable unique_ids SHALL ensure that entity IDs customised by the user in the HA entity registry are not reset when the options flow saves and the entry reloads.

#### Scenario: Custom entity ID survives options flow save
- **WHEN** the user has renamed `number.krowi_energy_management_electricity_vat_rate` to `number.my_vat`
- **WHEN** the user saves the electricity options flow (e.g. changes the unit)
- **THEN** after reload the entity's entity_id SHALL still be `number.my_vat`
- **THEN** the entity's unique_id SHALL remain `electricity_vat_rate` (unchanged)

---

### Requirement: Entity rename warning in HA Repairs
When a user renames any entity belonging to this component, a warning SHALL be raised in the HA Repairs panel to inform the user that sensors may be tracking a stale entity ID until the next restart.

The warning SHALL be per config entry (electricity and gas raise separately). It SHALL clear automatically when the entry next loads (on restart or reload).

#### Scenario: Warning raised after entity rename
- **WHEN** the user renames any `krowi_energy_management` entity in the HA entity registry
- **THEN** a warning issue SHALL appear in the HA Repairs panel
- **THEN** the issue SHALL identify the affected entry (electricity or gas)

#### Scenario: Warning clears on restart
- **WHEN** HA restarts (or the entry is reloaded) after a rename
- **THEN** the Repairs issue SHALL no longer be present
- **THEN** sensors SHALL re-register their listeners on the current entity IDs

#### Scenario: Rename of sibling entry does not affect other entry's issue
- **WHEN** a gas entity is renamed
- **THEN** only the gas entry's issue SHALL be raised
- **THEN** the electricity entry's Repairs state SHALL be unaffected
