## MODIFIED Requirements

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

### Requirement: Domain-aware options flow
Each config entry SHALL have an options flow that shows only the fields relevant to its domain type, pre-populated with current values. The settings entry SHALL have an options flow showing only the language selector.

#### Scenario: Options flow for settings entry shows only language selector
- **WHEN** user opens configure for the Settings entry
- **THEN** only the language selector SHALL be shown, pre-populated with the current language value

#### Scenario: Options flow for electricity entry shows only electricity fields
- **WHEN** user opens configure for the Electricity entry
- **THEN** only electricity-specific fields SHALL be shown (current price entity, FX entity, export template)
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

### Requirement: Duplicate domain prevention
The config flow SHALL prevent creating a second config entry for an already-configured domain or settings type.

#### Scenario: User tries to add Electricity when it already exists
- **WHEN** an electricity config entry already exists
- **WHEN** user opens the config flow and selects `Electricity`
- **THEN** the flow SHALL abort with an `already_configured` error

#### Scenario: User tries to add Settings when it already exists
- **WHEN** a settings config entry already exists
- **WHEN** user opens the config flow and selects `Settings`
- **THEN** the flow SHALL abort with an `already_configured` error

#### Scenario: Adding Gas is allowed when only Electricity exists
- **WHEN** an electricity config entry exists but no gas entry
- **WHEN** user opens the config flow and selects `Gas`
- **THEN** the flow SHALL proceed normally and create the gas entry
