# Spec: config-flow

## Purpose

Defines the config flow and options flow for the `krowi_energy_management` integration, including multi-entry domain setup, per-domain data shapes, duplicate prevention, and entity stability guarantees.

## Requirements

### Requirement: Multi-entry domain-based config flow with menu step
The component SHALL support multiple config entries, one per energy domain plus one optional settings entry. Setup SHALL use HA's menu step to present a domain/settings picker before domain-specific fields.

#### Scenario: User opens config flow for the first time
- **WHEN** user adds the integration
- **THEN** a menu step SHALL be shown with three options: `Electricity`, `Gas`, and `Settings`

#### Scenario: User selects Electricity
- **WHEN** user selects `Electricity` from the menu
- **THEN** an Electricity-specific form SHALL be shown with the fields defined in the Electricity config entry data shape
- **THEN** on submit a new config entry SHALL be created with `domain_type = "electricity"` and title `"Electricity"`

#### Scenario: User selects Gas
- **WHEN** user selects `Gas` from the menu
- **THEN** a Gas-specific form SHALL be shown with the fields defined in the Gas config entry data shape
- **THEN** on submit a new config entry SHALL be created with `domain_type = "gas"` and title `"Gas"`

#### Scenario: User selects Settings
- **WHEN** user selects `Settings` from the menu
- **THEN** a Settings form SHALL be shown with a language selector
- **THEN** on submit a new config entry SHALL be created with `domain_type = "settings"` and title `"Settings"`

---

### Requirement: Settings config entry data shape
A settings config entry SHALL store the following fields:

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `domain_type` | `"settings"` | Yes | — |
| `language` | `"en" \| "nl"` | Yes | `"en"` |

#### Scenario: Settings entry contains all fields after setup
- **WHEN** the settings config flow step is submitted
- **THEN** the resulting config entry SHALL contain both fields with correct types

---

### Requirement: Electricity config entry data shape
An electricity config entry SHALL store the following fields:

| Field | Type | Required | Default |
|---|---|---|---|
| `domain_type` | `"electricity"` | Yes | — |
| `export_template` | string (Jinja2) | Yes | — |

The `low_price_cutoff` field SHALL be stored in the config entry **options** (not data), so it can be changed without reconfiguring:

| Field | Type | Required | Default |
|---|---|---|---|
| `low_price_cutoff` | `float` | No | `1.0` |

The `unit`, `current_price_entity`, and `fx_rate_entity` fields are removed from the electricity config entry. `unit` is always `c€/kWh` (hardcoded). `current_price_entity` and `fx_rate_entity` are no longer applicable as the spot price is fetched internally.

#### Scenario: Electricity entry contains only the new fields after fresh setup
- **WHEN** a user completes the electricity config flow on a fresh install
- **THEN** the resulting config entry data SHALL contain exactly `domain_type` and `export_template`
- **THEN** the entry SHALL NOT contain `unit`, `current_price_entity`, or `fx_rate_entity`

#### Scenario: low_price_cutoff is stored in options with default
- **WHEN** the user does not modify `low_price_cutoff` in the options flow
- **THEN** `low_price_cutoff` SHALL default to `1.0` when read from `{**entry.data, **entry.options}`

#### Scenario: User changes low_price_cutoff via options flow
- **WHEN** the user submits the electricity options flow with `low_price_cutoff = 0.9`
- **THEN** `entry.options["low_price_cutoff"]` SHALL be `0.9`
- **THEN** the electricity entry SHALL reload so the store picks up the new cutoff

---

### Requirement: Config entry migration v1 to v2
The component SHALL implement `async_migrate_entry` in `__init__.py`. For electricity config entries at `VERSION = 1`, the migration SHALL:
1. Remove `current_price_entity` and `fx_rate_entity` from `entry.data` if present
2. Remove `unit` from `entry.data` if present
3. Set `entry.version = 2`

The migration SHALL be idempotent — if the fields are already absent, no error occurs.

#### Scenario: v1 electricity entry is migrated on load
- **WHEN** a v1 electricity config entry with `current_price_entity`, `fx_rate_entity`, and `unit` is loaded
- **THEN** `async_migrate_entry` SHALL strip those three fields
- **THEN** the resulting entry SHALL have `version = 2` and contain only `domain_type` and `export_template`

#### Scenario: v1 settings and gas entries are migrated without changes
- **WHEN** a v1 settings or gas config entry is loaded
- **THEN** `async_migrate_entry` SHALL set `version = 2` without modifying any data fields

#### Scenario: v2 entries are not re-migrated
- **WHEN** a v2 config entry is loaded
- **THEN** `async_migrate_entry` SHALL NOT be called

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
The config flow SHALL prevent creating a second config entry for an already-configured domain or settings type.

#### Scenario: User tries to add Electricity when it already exists
- **WHEN** an electricity config entry already exists
- **WHEN** user opens the config flow and selects `Electricity`
- **THEN** the flow SHALL abort with an `already_configured` error
- **THEN** no new config entry SHALL be created

#### Scenario: User tries to add Settings when it already exists
- **WHEN** a settings config entry already exists
- **WHEN** user opens the config flow and selects `Settings`
- **THEN** the flow SHALL abort with an `already_configured` error

#### Scenario: Adding Gas is allowed when only Electricity exists
- **WHEN** an electricity config entry exists but no gas entry
- **WHEN** user opens the config flow and selects `Gas`
- **THEN** the flow SHALL proceed normally and create the gas entry

---

### Requirement: Domain-aware options flow
Each config entry SHALL have an options flow that shows only the fields relevant to its domain type, pre-populated with current values. The settings entry SHALL have an options flow showing only the language selector.

#### Scenario: Options flow for settings entry shows only language selector
- **WHEN** user opens configure for the Settings entry
- **THEN** only the language selector SHALL be shown, pre-populated with the current language value

#### Scenario: Options flow for electricity entry shows only electricity fields
- **WHEN** user opens configure for the Electricity entry
- **THEN** only electricity-specific fields SHALL be shown (export template, low_price_cutoff)
- **THEN** all fields SHALL be pre-populated with the current entry values

#### Scenario: Options flow for gas entry shows only gas fields
- **WHEN** user opens configure for the Gas entry
- **THEN** only gas-specific fields SHALL be shown (unit, current price entity)
- **THEN** all fields SHALL be pre-populated with the current entry values

#### Scenario: Saving options triggers entry reload
- **WHEN** user saves the options flow for any entry
- **THEN** that entry SHALL reload completely
- **THEN** all entities belonging to that entry SHALL be re-created with the updated configuration
- **THEN** entities from other domain entries SHALL NOT be affected (except when language changes, which reloads all domain entries)

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
