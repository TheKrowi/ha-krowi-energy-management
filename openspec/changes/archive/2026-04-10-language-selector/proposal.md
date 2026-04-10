## Why

Entity display names are currently hardcoded in English in the Python source. Most users of this Belgian energy management integration will want Dutch names, but some prefer English. A language selector in the configuration allows the user to choose once, globally, and have all entity names reflect that choice on next reload.

## What Changes

- Add a `Settings` option to the config flow menu — creates a dedicated `settings` config entry
- The settings entry stores a `language` field (`"en"` or `"nl"`)
- Only one settings entry is allowed (duplicate prevention)
- All number and sensor entities look up their display name from a `NAMES` dict keyed by `(uid, language)` at setup time
- Changing language via options flow on the settings entry triggers a reload of the settings entry; all domain entries must also reload to pick up the new language
- `strings.json` / `en.json` updated to include Settings config and options flow strings
- `nl.json` created with Dutch translations for the Settings flow

## Capabilities

### New Capabilities

- `language-selector`: Defines the settings config entry, language options (EN/NL), name resolution logic, and reload behaviour when language changes

### Modified Capabilities

- `config-flow`: Adds the `settings` menu option, Settings entry data shape, duplicate prevention for the settings entry, and options flow for the settings entry

## Impact

- `config_flow.py` — new `settings` menu option, new `SettingsConfigStep` form, new `SettingsOptionsFlow`, duplicate check for settings entry
- `const.py` — new `DOMAIN_TYPE_SETTINGS = "settings"`, `CONF_LANGUAGE = "language"`, `LANG_EN = "en"`, `LANG_NL = "nl"`, `NAMES` dict mapping `(uid, lang)` → display name for all 18 entities
- `number.py` — `_attr_name` set via `NAMES` lookup using language from settings entry
- `sensor.py` — `_attr_name` set via `NAMES` lookup using language from settings entry
- `strings.json` — new `settings` menu option and config/options step strings
- `translations/en.json` — new strings for settings flow
- `translations/nl.json` — new file with Dutch translations for Settings flow UI strings
