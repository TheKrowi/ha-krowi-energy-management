## ADDED Requirements

### Requirement: Settings entry stores global language preference
The component SHALL support a third config entry type with `domain_type = "settings"`. This entry SHALL store a `language` field with value `"en"` or `"nl"`. Only one settings entry SHALL be allowed per integration instance.

#### Scenario: User creates a settings entry and selects NL
- **WHEN** user opens the config flow and selects `Settings`
- **THEN** a form SHALL be shown with a language selector offering `English` and `Nederlands`
- **THEN** on submit a config entry SHALL be created with `domain_type = "settings"` and `language = "nl"`

#### Scenario: Duplicate settings entry is prevented
- **WHEN** a settings entry already exists
- **WHEN** user opens the config flow and selects `Settings`
- **THEN** the flow SHALL abort with an `already_configured` error

#### Scenario: Settings entry defaults to English if language not set
- **WHEN** no settings entry exists
- **THEN** all entity names SHALL fall back to English

---

### Requirement: Entity names resolve from language preference at setup time
At setup time, each number and sensor entity SHALL look up its display name from the `NAMES` dict in `const.py` using the `(uid, language)` key. The language SHALL be read from the settings config entry. If no settings entry exists, `"en"` SHALL be used as the fallback.

#### Scenario: Language is NL — entities get Dutch names
- **WHEN** the settings entry has `language = "nl"`
- **WHEN** the electricity entry is loaded
- **THEN** `electricity_tariff_green_energy_contribution` entity name SHALL be `"Groene stroom bijdrage"`

#### Scenario: Language is EN — entities get English names
- **WHEN** the settings entry has `language = "en"`
- **WHEN** the electricity entry is loaded
- **THEN** `electricity_tariff_green_energy_contribution` entity name SHALL be `"Green energy contribution"`

#### Scenario: No settings entry — English fallback
- **WHEN** no settings entry exists
- **WHEN** the electricity entry is loaded
- **THEN** all entity names SHALL use English

---

### Requirement: Changing language triggers full domain entry reload
When the user saves the settings options flow with a new language value, the settings entry SHALL trigger a reload of all other domain entries so entities pick up the new names.

#### Scenario: User changes language from EN to NL
- **WHEN** user opens Settings options flow and changes language from `"en"` to `"nl"`
- **WHEN** user saves
- **THEN** the settings entry SHALL reload
- **THEN** all electricity and gas entries SHALL reload
- **THEN** after reload all entity names SHALL reflect the new language
