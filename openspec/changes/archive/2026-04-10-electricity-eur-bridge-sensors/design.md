## Context

The component exposes electricity prices in `c€/kWh` — the natural scale for Belgian tariffs (e.g. `4.271 c€/kWh` rather than `0.04271 €/kWh`). The HA Energy Dashboard only accepts sensors whose unit is `EUR/<energy unit>` (e.g. `EUR/kWh`). This means the existing `electricity_price_import` and `electricity_price_export` sensors cannot be linked to the energy dashboard directly.

Additionally, the current config flow presents a `unit` selector for electricity, offering `c€/kWh`, `€/kWh`, and `€/MWh`. Since electricity is now always `c€/kWh`, this selector is unnecessary and confusing.

## Goals / Non-Goals

**Goals:**
- Add two derived bridge sensors (`EUR/kWh`) so the HA Energy Dashboard can consume import and export prices.
- Remove the `unit` selector from the electricity config and options flow; hardcode `c€/kWh` for all electricity entities.

**Non-Goals:**
- Gas unit changes — gas retains the unit selector.
- Data migration of existing config entries — the `unit` field may still exist in old entries but will be ignored for electricity; no migration step is needed.
- Changing how the underlying import/export prices are computed.

## Decisions

### 1. Bridge sensors derive reactively from existing price sensors (not from raw inputs)

**Decision:** `electricity_price_import_eur` listens to the state of `electricity_price_import` via `async_track_state_change_event`; same for export. It divides the state value by 100.

**Alternatives considered:**
- *Recompute from raw inputs* — would duplicate all the computation logic (Nord Pool entity, FX, surcharge, VAT). More robustness but significant code duplication with no real benefit.
- *Template sensor* — would work, but inconsistent with how other computed sensors are implemented in this codebase.

**Rationale:** The upstream sensors already handle all edge cases (unavailable, unknown, FX). The bridge only needs to propagate state or divide by 100.

### 2. Propagate `unavailable` / `unknown` from source sensor

**Decision:** If the source sensor state is not a parseable float, the bridge sensor sets its state to `None` (which HA renders as `unavailable`). No special `unknown` string is emitted.

**Rationale:** Consistent with how `GasCurrentPriceSensor` and `ElectricityImportPriceSensor` handle unavailable upstream entities (`safe_float_state` returns `None`).

### 3. Electricity unit hardcoded via constant, not read from config entry

**Decision:** Add `UNIT_ELECTRICITY = "c€/kWh"` to `const.py`. All electricity code paths use this constant directly. The `CONF_UNIT` key is no longer written to electricity config entries.

**Alternatives considered:**
- *Keep `CONF_UNIT` in entry, just default it* — leaves dead config data in entries; misleading.
- *Add a migration step* — unnecessary overhead; old entries simply won't have `unit` ignored silently.

**Rationale:** Removing the field entirely from the electricity schema makes the intent explicit and removes one user-facing choice with a wrong answer.

### 4. Bridge sensors belong to the same Electricity device

**Decision:** `electricity_price_import_eur` and `electricity_price_export_eur` use the same `DeviceInfo` as the other electricity sensors (`identifiers={(DOMAIN, f"{entry_id}_electricity")}`).

**Rationale:** All electricity sensors appear under one device in HA. No reason to split.

### 5. Source entity ID resolved via entity registry at subscription time

**Decision:** Bridge sensors resolve the source entity ID from the entity registry using `_resolve_entity_id(hass, "sensor", UID_ELECTRICITY_PRICE_IMPORT)` at `async_added_to_hass` time, same as other dependent sensors.

**Rationale:** Consistent with existing pattern. Entity IDs can be renamed by the user; the registry lookup is authoritative.

## Risks / Trade-offs

- **Startup ordering** — If the bridge sensor is added before the source sensor is fully set up, the initial `_update()` will find no state and emit `None`. This is acceptable — the source sensor will emit a state change event shortly after, which the bridge will catch.
- **Breaking existing config entries** — Old electricity entries have a `unit` key stored in `data`. This key is now ignored for electricity. If a user had set `€/kWh` or `€/MWh`, their tariff number entities will silently switch to `c€/kWh` displayed unit without rescaling stored values. Since this component is pre-release and the user is the sole audience, this is acceptable.
- **`UNIT_OPTIONS` still used for gas** — `UNIT_OPTIONS` in `const.py` is now gas-only. Renaming it to `GAS_UNIT_OPTIONS` is cleaner but not strictly required; left as a judgement call for the implementer.

## Migration Plan

No data migration steps required. Old electricity config entries with a stored `unit` value will simply have that key ignored. No HA version constraints apply. No restart beyond the normal integration reload is needed.

## Open Questions

None — all decisions resolved during exploration phase.
