## Why

Entity unique IDs, entity IDs, and display names across `number` and `sensor` platforms are inconsistent: number UIDs use a flat `electricity_*_rate` pattern while sensors use a different flat pattern, names mix Dutch and English, and there is no structural grouping to distinguish tariff inputs from derived price outputs. This is the pre-release window — UIDs cannot be changed safely once a GitHub Release exists.

## What Changes

- **BREAKING** Rename all 18 entity unique IDs (and corresponding entity IDs) to a consistent, grouped scheme using `_tariff_` and `_current_price_` infixes
- Rename all sensor `_attr_name` values to consistent English names aligned with the Dutch naming pattern
- Number entity Dutch names remain as-is (already correct in `strings.json` / `en.json`)
- Update `const.py` UID constants to reflect new values
- Update `strings.json` and `translations/en.json` entity keys to match new UIDs
- Update all `_resolve_entity_id` call sites in `sensor.py` that reference old UIDs

## Capabilities

### New Capabilities

- `consistent-entity-ids`: Defines the canonical UID scheme for all number and sensor entities — grouping rules, infix conventions, and the full UID-to-name mapping table

### Modified Capabilities

- `electricity-sensors`: UID and display name changes for all electricity sensor entities
- `electricity-tariff-entities`: UID changes for all electricity number entities
- `electricity-eur-bridge-sensors`: UID changes for the two EUR bridge sensors
- `gas-sensors`: UID and display name changes for all gas sensor entities
- `gas-tariff-entities`: UID changes for all gas number entities

## Impact

- `const.py` — all `UID_*` constant values change
- `number.py` — no logic changes, picks up new UIDs automatically via constants
- `sensor.py` — `_attr_unique_id`, `entity_id`, `_attr_name` in every sensor class; `_resolve_entity_id` call sites that reference UID constants (automatically correct via constants)
- `strings.json` — entity section keys must match new UIDs
- `translations/en.json` — entity section keys must match new UIDs
- Existing HA installations must re-add the integration (acceptable at pre-release, before any GitHub tag exists)
