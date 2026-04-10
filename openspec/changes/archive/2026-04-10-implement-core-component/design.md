## Context

No Python code exists yet for `krowi_energy_management`. The OpenAPI spec (`openapi/component.yaml`) fully documents the intended interface: 10 number entities, 6 sensor entities, a config/options flow, and reactive computation. The upstream data sources are documented in `openapi/upstream.yaml`. All key design decisions were made before implementation started (see decisions below).

The component is HACS-compatible and targets Belgian users, though Nord Pool and TTF DAM entity IDs are fully configurable to support other markets.

## Goals / Non-Goals

**Goals:**
- Implement all files in `custom_components/krowi_energy_management/` matching the OpenAPI interface spec
- Reactive computation: sensors update immediately when any upstream entity state changes
- Runtime unit auto-conversion: read `unit_of_measurement` from upstream entity attributes; auto-scale magnitude (kWh↔MWh↔Wh) and optionally apply FX multiplier
- Unavailability propagation: computed sensors become `unavailable` if any required upstream is missing or unavailable
- HACS-ready: `hacs.json`, `manifest.json`, `strings.json`, `translations/en.json`

**Non-Goals:**
- Unit tests / test suite
- Historical data visualization or statistics sensors beyond what's in the spec
- Multi-currency support beyond the optional FX sensor multiplier
- Supporting HA versions below stable at time of implementation
- Any outbound HTTP calls from this component (upstream data comes via HA entity states only)

## Decisions

### D1: No DataUpdateCoordinator — pure reactive entities

**Decision**: All sensors react to `async_track_state_change_event` (and `async_track_template_result` for the export sensor). No polling, no coordinator.

**Alternatives considered**: Using a coordinator with a short polling interval (e.g. 1 min). Rejected — the upstream entities (Nord Pool, TTF DAM) already poll on their own schedule. Adding a coordinator would introduce unnecessary latency and coupling.

**Rationale**: Surcharge sensors depend only on the component's own number entities; price sensors depend on upstream HA entities. State-change tracking is instantaneous and well-supported in HA.

---

### D2: Runtime unit auto-conversion based on entity attributes

**Decision**: At computation time, read `state.attributes["unit_of_measurement"]` from the Nord Pool and TTF DAM entities. Convert the raw value to the component's configured unit before applying the formula.

Each supported unit string is decomposed into two independent factors:

| Unit string | currency_factor | magnitude_wh |
|---|---|---|
| `c€/Wh` | 0.01 | 1 |
| `€/Wh` | 1.0 | 1 |
| `c€/kWh` | 0.01 | 1_000 |
| `€/kWh` | 1.0 | 1_000 |
| `c€/MWh` | 0.01 | 1_000_000 |
| `€/MWh` | 1.0 | 1_000_000 |

Conversion factor (O(1), no lookup table over pairs):
```
factor = (from_currency_factor / to_currency_factor) * (to_magnitude_wh / from_magnitude_wh)
result = value * factor
```

This handles all 36 unit-pair combinations automatically. Example — `€/MWh` → `c€/kWh`:
```
factor = (1.0 / 0.01) * (1_000 / 1_000_000) = 100 * 0.001 = 0.1
```

If the upstream unit string is not in the known set, return `None` and log a warning.

FX conversion (if `fx_rate_entity` is configured): apply magnitude conversion first, then multiply the result by `fx_sensor_state`.  Order: magnitude → FX.

**Alternatives considered**: Requiring users to set Nord Pool to the same unit as `electricity_unit`. Rejected — too fragile and unintuitive; fails silently if Nord Pool config changes.

**Rationale**: The Nord Pool HA integration exposes `unit_of_measurement` in entity attributes, making runtime detection reliable. The conversion logic is simple arithmetic and centralised in one helper function.

---

### D3: FX rate via optional sensor entity reference

**Decision**: Add an optional `fx_rate_entity` field to the config entry. If set, the component reads that entity's state as a float multiplier. If not set (default), FX = 1.0 (no conversion).

**Alternatives considered**:
- Live FX API call: requires outbound HTTP, contradicts the component's "no outbound calls" design, adds API key management and failure modes.
- Hardcoded fallback rate: inaccurate and misleading.
- Number entity for FX rate: user must maintain it manually without any connection to real rates.

**Rationale**: A sensor entity reference lets the user connect any HA integration that provides live exchange rates (e.g., a scraper, another custom component, or a `rest` sensor). It's flexible, doesn't add maintenance burden to this component, and defaults to a no-op for EUR users.

---

### D4: Export price rendered via `async_track_template_result`

**Decision**: The `electricity_current_price_export` sensor uses HA's `async_track_template_result` API to render the user-supplied Jinja2 template reactively. All entities referenced in the template are automatically tracked.

**Alternatives considered**: Re-rendering on a fixed interval. Rejected — introduces unnecessary lag and misses rapid price changes.

**Rationale**: `async_track_template_result` is the canonical HA mechanism for reactive Jinja2 evaluation. Template sensors in HA core use it. No custom entity tracking needed.

---

### D5: Initial value 0 for all number entities

**Decision**: When a number entity is first created (no restore state), its native value is 0.

**Alternatives considered**: Sensible Belgian defaults (e.g. VAT 21%/6%). Rejected — hardcoding Belgian rates would be misleading for non-Belgian users and the "right" defaults change over time.

**Rationale**: Zero is explicit. Users will see blank/zero values and know to configure them. The HA UI makes it easy to update number entities.

---

### D6: Unavailability propagation

**Decision**: If any upstream entity required by a sensor formula is `unavailable`, `unknown`, or missing (`hass.states.get()` returns `None`), the computed sensor's state is set to `STATE_UNAVAILABLE`.

**Alternatives considered**: Keep last known value. Rejected — stale prices are dangerous in an energy management context. A user acting on an outdated import price could make incorrect decisions.

**Rationale**: Explicit unavailability is safer and more transparent.

---

### D7: Two devices — Electricity and Gas

**Decision**: All entities are grouped under two HA `DeviceEntry` instances: one for electricity (identifier: `{DOMAIN, f"{entry_id}_electricity"}`) and one for gas (identifier: `{DOMAIN, f"{entry_id}_gas"}`). Both are children of the same config entry and integration.

**Alternatives considered**: Single device containing all 16 entities. Rejected — the electricity/gas separation is a meaningful domain boundary. Two devices make the UI clearly separate concerns, and adding future domains (water, solar) follows the same pattern with no structural change.

**Rationale**: The two-device pattern scales naturally. Adding a third domain = adding a third device, no refactoring needed. HA handles sibling devices under the same integration cleanly.

---

### D8: Drop `tariff_` and `current_` infixes from entity unique IDs

**Decision**: Remove the `tariff_` infix from number entity unique IDs and the `current_` infix from sensor entity unique IDs. The concepts are implicit — all number entities in this component are tariff rates; all price sensors are current prices.

Before → After:
- `electricity_tariff_vat_rate` → `electricity_vat_rate`
- `electricity_tariff_distribution_transport_rate` → `electricity_distribution_transport_rate`
- `electricity_tariff_total_surcharge_rate` → `electricity_surcharge_rate`
- `electricity_tariff_surcharge_formula` → `electricity_surcharge_formula`
- `electricity_current_price_import` → `electricity_price_import`
- `electricity_current_price_export` → `electricity_price_export`
- `gas_tariff_*` → `gas_*` (same pattern for all gas number entities)
- `gas_current_price` → `gas_price`

**Rationale**: Shorter entity IDs reduce friction in automations and developer tools. The entity type (number vs sensor) and device grouping (electricity vs gas device) already provide the context that `tariff_` and `current_` were trying to convey.

### D9: Multi-entry config model with HA menu step flow

**Decision**: Each energy domain (electricity, gas, future: water) gets its own HA config entry. Setup uses HA's menu step API (`async_step_menu`) to present a button-list domain picker before domain-specific fields. One class handles all domains; the options flow reads `entry.data["domain_type"]` to show only relevant fields.

Config entry data shapes:

```python
# Electricity entry
{
    "domain_type": "electricity",
    "unit": "€/kWh",
    "current_price_entity": "sensor.nord_pool_be_current_price",
    "fx_rate_entity": "",           # optional, empty = no FX
    "export_template": "{{ ... }}"
}

# Gas entry
{
    "domain_type": "gas",
    "unit": "€/MWh",
    "current_price_entity": "sensor.krowi_ttf_dam_30d_avg"
}
```

Entry title is the capitalised domain name: `"Electricity"`, `"Gas"`.

Duplicate prevention: in `async_step_menu`, check all existing config entries for the selected `domain_type`; if one already exists, abort with a `already_configured` error — do not create a second entry.

User-customised entity IDs (renamed via HA UI) are preserved across options flow saves because unique_ids never change — HA's entity registry maps the stable unique_id to whatever entity_id the user set.

**Alternatives considered**:
- Single config entry with all domains: rejected — editing gas settings requires touching the same form as electricity; adding water risks breaking existing config.
- Dropdown domain selector (Option A): rejected in favour of menu step — button-list picker is a better UX for "choose what you want to configure" and is the idiomatic HA menu step pattern.

**Rationale**: Per-domain entries give true isolation: options flow for electricity cannot affect gas, and adding a new domain in the future is adding a new menu item + a new step + new entities — no modification to existing entries or entities.

### D10: Entity rename warning via HA Repairs

**Decision**: When any entity belonging to this component is renamed by the user in the HA entity registry, raise a warning issue in the HA Repairs panel (`ir.async_create_issue`) for the affected entry. The issue clears automatically on the next entry load (restart or reload).

**Trigger**: Listen to `EVENT_ENTITY_REGISTRY_UPDATED` within `async_setup_entry`. Fire when `action == "update"` and `"entity_id"` appears in the changed keys and the entity belongs to this config entry.

**Lifecycle**:
- `async_setup_entry`: register the registry listener; delete any pre-existing issue for this entry (covers the restart case)
- Registry event fires: raise `ir.async_create_issue` with `severity=IssueSeverity.WARNING`, `issue_id=f"entity_renamed_{entry_id}"`
- `async_unload_entry`: unsubscribe listener; delete the issue

One issue per config entry — electricity and gas raise independently.

**Alternatives considered**: Persistent notification (too passive, no acknowledgement flow); options flow description text (only visible if user opens Configure).

**Rationale**: The HA Repairs panel is the idiomatic surface for "something needs your attention" — it shows a badge on the Settings menu and requires the user to explicitly dismiss it. The warning communicates that sensors may be tracking a stale entity ID until the next restart, which is important for correctness.

---

## Risks / Trade-offs

- **Electricity `current_price_entity` not installed or unavailable** → all electricity price sensors become `unavailable`. Mitigation: clear error log message.
- **Gas `current_price_entity` not installed or unavailable** → gas price sensor becomes `unavailable`. Mitigation: same — log a clear message.
- **FX sensor returning non-numeric value** → treat as unavailable; propagate to computed sensor. Mitigation: `float()` with fallback to `None`; log a warning.
- **Unit not recognised** → if `unit_of_measurement` from upstream doesn't match any known unit string, log a warning and set sensor unavailable. Avoids silent wrong math.
- **Jinja2 template rendering error** → `async_track_template_result` calls the result callback with an error state. The export sensor should set itself unavailable on template errors and log the template error message.
- **User changes `electricity_unit` or `gas_unit` via options flow** → triggers full component reload (standard HA behaviour for options flow). All entities are re-created with the new unit. Number entity restore values are unit-agnostic floats, so they survive the reload — but their meaning changes if the user changes the unit. Mitigation: document clearly in the UI that changing the unit does not rescale existing values.
