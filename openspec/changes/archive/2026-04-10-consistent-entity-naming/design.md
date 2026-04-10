## Context

All entity unique IDs are currently flat strings under the domain prefix (`electricity_*`, `gas_*`) with no structural grouping. Number entities use a `_rate` suffix inconsistently (`_contribution_rate` vs `_rate`). Sensor display names in code are English while number display names are Dutch. There is no visual or semantic separation between tariff input entities and derived price output entities.

HA entity `unique_id` values are permanent identifiers stored in the entity registry. Changing them after a release breaks existing entries. The project has no GitHub Release yet — this is the correct window to make these changes.

## Goals / Non-Goals

**Goals:**
- Establish a canonical UID scheme with clear structural groupings
- Make all sensor `_attr_name` values English (consistent language in code)
- Ensure `strings.json` / `en.json` keys match the new UIDs
- All changes landed in a single commit before any GitHub tag is created

**Non-Goals:**
- Adding Dutch translations (`nl.json`) — that is the `language-selector` change
- Changing any computation logic or config flow behaviour
- Rescaling stored entity values

## Decisions

### UID grouping scheme

Use infixes to group entities semantically:

| Infix | Entities |
|-------|----------|
| `_tariff_` | All user-editable tariff rate number inputs (`electricity_tariff_*`, `gas_tariff_*`) |
| `_tariff_total_` | Derived sensor that sums tariff inputs (`electricity_tariff_total_surcharge`, `gas_tariff_total_surcharge`) |
| `_current_price_` | Derived price output sensors (`electricity_current_price_*`, `gas_current_price`) |
| _(no infix)_ | VAT entities — VAT applies to total price, not a tariff component (`electricity_vat`, `gas_vat`) |

**Alternative considered — keep flat:** Rejected. Without grouping, tariff input entities and derived price sensors are visually indistinguishable in the HA entity list.

### Drop `_rate` suffix from UIDs

`_rate` is redundant when the UID already describes a rate (e.g. `electricity_tariff_excise_duty` is obviously a rate). Removing it shortens UIDs and eliminates the `_contribution_rate` vs `_rate` inconsistency.

**Alternative considered — keep `_rate`:** Rejected. It would still be inconsistent across entities unless `_contribution_rate` was also normalised to `_rate`, which loses meaning.

### VAT outside `_tariff_` group

VAT is not a tariff component — it is applied to the full price (spot + surcharge). Placing it under `_tariff_` would be semantically incorrect. `electricity_vat` and `gas_vat` are the correct UIDs.

### Sensor display names → English in code

Dutch names should not be hardcoded as the fallback in `_attr_name`. The correct pattern is: English in code, translations in language files. This change sets English names in code; the `language-selector` change will introduce Dutch names via a config-driven lookup.

## Risks / Trade-offs

- **Existing HA installations break** → Acceptable: no GitHub Release exists yet. Users must re-add the integration. Documented in commit message.
- **`_resolve_entity_id` call sites in `sensor.py`** → These reference UID constants from `const.py` directly, so updating `const.py` values is sufficient. No string literals to hunt down.
- **`strings.json` / `en.json` keys** → Must be updated manually to match new UIDs, otherwise HA's translation lookup silently fails and falls back to the hardcoded `_attr_name`.
