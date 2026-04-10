## 1. Add constants to const.py

- [x] 1.1 Add `DOMAIN_TYPE_SETTINGS = "settings"`, `CONF_LANGUAGE = "language"`, `LANG_EN = "en"`, `LANG_NL = "nl"` constants
- [x] 1.2 Add `NAMES` dict mapping `(uid, language)` → display name for all 18 entities (EN and NL values from the canonical table in `consistent-entity-ids` spec)
- [x] 1.3 Add helper constant `LANGUAGE_OPTIONS = [LANG_EN, LANG_NL]`

## 2. Update config_flow.py

- [x] 2.1 Add `Settings` option to the menu step (`menu_options` dict)
- [x] 2.2 Add `async_step_settings` — shows language selector (select with EN/NL options), creates entry with `domain_type = "settings"`, title `"Settings"`
- [x] 2.3 Add duplicate prevention for the settings entry in `async_step_settings` (abort with `already_configured` if a settings entry exists)
- [x] 2.4 Add `SettingsOptionsFlow` class with `async_step_init` — shows language selector pre-populated with current value, saves on submit
- [x] 2.5 Wire `SettingsOptionsFlow` into `async_get_options_flow` alongside existing electricity/gas options flows
- [x] 2.6 Add reload-all-domain-entries logic in `SettingsOptionsFlow.async_step_init` after saving: iterate `hass.config_entries.async_entries(DOMAIN)`, reload any entry with `domain_type` in `[DOMAIN_TYPE_ELECTRICITY, DOMAIN_TYPE_GAS]`

## 3. Add language resolution helper

- [x] 3.1 Add `_get_language(hass)` helper (in `const.py` or a new `utils`-adjacent location) that scans `hass.config_entries.async_entries(DOMAIN)` for a settings entry and returns its `language` value, defaulting to `LANG_EN`

## 4. Update number.py

- [x] 4.1 In `async_setup_entry`, call `_get_language(hass)` to resolve the current language
- [x] 4.2 Pass `language` into `KrowiNumberEntity` (or set it on the descriptor before instantiation)
- [x] 4.3 In `KrowiNumberEntity.__init__`, set `self._attr_name = NAMES.get((descriptor.unique_id_suffix, language), NAMES[(descriptor.unique_id_suffix, LANG_EN)])`

## 5. Update sensor.py

- [x] 5.1 In `async_setup_entry`, call `_get_language(hass)` to resolve the current language
- [x] 5.2 Pass `language` into each sensor class constructor
- [x] 5.3 In each sensor `__init__`, set `self._attr_name` via `NAMES.get((uid, language), NAMES[(uid, LANG_EN)])` instead of hardcoded string

## 6. Update strings.json and translation files

- [x] 6.1 Add `settings` to `config.step.menu.menu_options` in `strings.json`
- [x] 6.2 Add `settings` config step definition (title, data: language) to `strings.json`
- [x] 6.3 Add `settings_options` options step definition to `strings.json`
- [x] 6.4 Mirror all strings.json changes into `translations/en.json`
- [x] 6.5 Create `translations/nl.json` with Dutch translations
