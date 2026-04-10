## Context

Entity display names are hardcoded in the Python source. The `consistent-entity-naming` change establishes English as the code-level default, but Belgian users typically want Dutch names. This change adds a global language selector so the user can choose EN or NL once, and all 18 entity names reflect that choice after a reload.

The integration uses a config-entry-per-domain model. There is no singleton or shared state object — each entry is independent. A dedicated `settings` entry is the cleanest way to store global preferences without coupling domain entries to each other.

## Goals / Non-Goals

**Goals:**
- One settings entry stores the language preference globally
- All entity names resolve from a static dict at setup time based on the stored language
- Changing language via options flow → reload of settings entry → reload of all domain entries → entities get new names
- `nl.json` is created for Dutch UI strings in the settings flow itself

**Non-Goals:**
- Live entity rename without reload (reload-on-change is acceptable and simpler)
- Support for languages beyond EN and NL
- Per-entry language overrides
- Renaming entities owned by other integrations

## Decisions

### Dedicated settings entry (Option A over shared hass.data)

A `settings` config entry with `domain_type = "settings"` stores the language. It is the third entry type alongside `electricity` and `gas`.

**Why:** A dedicated entry appears in the HA integrations panel with its own "Configure" button. The user can change language without re-running the full setup. It is persistent by design — HA saves it to `config/.storage/core.config_entries`.

**Alternative considered — store language in the first domain entry:** Rejected. It creates ordering dependencies between entries and makes the language field appear inside the electricity or gas options flow, which is semantically confusing.

**Alternative considered — hass.data only (no settings entry):** Rejected. `hass.data` is not persistent — language would reset to the hardcoded default on every restart.

### Language lookup via NAMES dict in const.py

A top-level `NAMES` dict in `const.py` maps `(uid, language)` → display name string. At setup time, each entity resolves its name by looking up `NAMES.get((uid, lang), NAMES[(uid, "en")])` — falling back to English if the UID is not found for the requested language.

**Why:** Centralises all translatable strings in one place. No runtime file I/O. Fast. Easy to extend to a third language later.

**Alternative considered — separate EN/NL dicts:** Equivalent complexity, slightly less ergonomic for lookup. Rejected in favour of the tuple-keyed dict.

### How entities find the settings entry

In `number.py` and `sensor.py`, the `async_setup_entry` functions receive only the current domain entry. To read the language, they scan `hass.config_entries.async_entries(DOMAIN)` and find the entry with `domain_type == "settings"`. If no settings entry exists (not yet configured), they fall back to `"en"`.

**Why:** Simple, no shared state required, consistent with other HA integrations that cross-reference entries.

### Reload chain when language changes

When the user saves the settings options flow:
1. HA reloads the settings entry (standard HA options flow behaviour)
2. `async_setup_entry` for settings entry iterates over all other domain entries and calls `hass.config_entries.async_reload(entry_id)` for each
3. Each domain entry reloads and entities are re-created with the new language

**Risk:** If a domain entry fails to reload, its entities retain the old language until the next manual reload or restart. This is acceptable — HA will surface any reload errors.

## Risks / Trade-offs

- **Settings entry missing** → Fallback to `"en"` silently. No error raised. Acceptable UX.
- **Reload chain causes brief unavailability** → All entities go unavailable for a moment during reload. Acceptable for a conscious user action.
- **NAMES dict maintenance** → Adding a new entity requires updating the dict. Mitigated by the `consistent-entity-ids` spec defining the canonical table as the single source of truth.
- **nl.json only covers settings flow UI** → Entity names come from `NAMES` dict, not from translation files. `nl.json` only needs the config/options flow label strings for the settings step.
