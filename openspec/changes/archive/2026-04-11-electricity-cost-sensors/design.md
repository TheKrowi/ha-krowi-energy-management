## Context

The electricity config entry already produces price sensors (`electricity_current_price_import_eur`, `electricity_current_price_export_eur`) but has no mechanism to accumulate actual monetary cost over time. The gas domain already solved this with `GasTotalCostSensor` (RestoreEntity, delta-based accumulator). This change mirrors that pattern for electricity, extended to handle the 4-register P1 meter (Fluvius: import/export × tariff 1/2) and adds derived aggregate sensors.

Current electricity options flow: `export_template`, `low_price_cutoff` — no meter entities.

## Goals / Non-Goals

**Goals:**
- 4 per-tariff accumulator sensors (RestoreEntity): import T1, import T2, export T1, export T2
- 2 derived total sensors (live formula): total import cost, total export revenue
- 1 derived net cost sensor (live formula, MEASUREMENT, can go negative)
- 8 new optional fields in the electricity options flow (4 meter + 4 price entity selectors)
- Defaults pointing to known P1 entity IDs and existing EUR/kWh price sensors
- EN + NL display names for all 7 sensors

**Non-Goals:**
- Time-of-use pricing logic (tariff 1/2 each get a configurable price entity — no automatic day/night switching)
- HA Energy Dashboard integration validation
- Any migration step (all new fields optional with defaults)

## Decisions

### D1 — Accumulator pattern: delta-based RestoreEntity (same as gas)

The 4 per-tariff sensors track `_last_kwh` per instance. On each meter state-change event:
```
delta_kwh = new_kwh − last_kwh
cost += delta_kwh × price_EUR_per_kWh
```
Rationale: consistent with gas, survives HA restarts via RestoreEntity, no external storage needed.

Alternative considered: polling — rejected (breaks no-coordinator principle).

### D2 — Aggregate sensors are purely derived (no own accumulator)

`electricity_total_import_cost`, `electricity_total_export_revenue`, and `electricity_net_cost` read the current numeric state of the 4 per-tariff sensors and recompute. They subscribe to state-change events on those 4 entities.

Rationale: eliminates drift risk. If any per-tariff sensor is restored at startup, the aggregates immediately reflect the correct value without needing their own restore. 

Alternative considered: independent accumulators for totals — rejected (two sources of truth, drift risk on restart).

### D3 — Price entity treated as EUR/kWh, no internal conversion

Whatever entity the user configures for each tariff's price is read directly and multiplied by Δkwh. Default points to `sensor.electricity_current_price_import_eur` / `sensor.electricity_current_price_export_eur`.

Rationale: mirrors gas (`UID_GAS_PRICE_EUR`), avoids silent unit errors. User is responsible for picking EUR/kWh sensor.

### D4 — Negative delta: re-anchor, preserve total

On a negative meter delta (meter replacement, P1 glitch), `_last_kwh` is updated to the new reading but nothing is added to the total.

Rationale: same as gas. Silently ignoring is safer than reversing an accumulator or crashing.

### D5 — Price unavailable: fall back to last known price

Each per-tariff sensor keeps `_last_known_price`. If the price entity is unavailable on a given tick, the last known value is used. If no price has ever been seen, the tick is skipped.

Rationale: Nord Pool outages are transient; skipping consumption ticks would silently under-count cost.

### D6 — No config entry version bump

All 8 new options keys are `vol.Optional` with defaults. `async_setup_entry` reads them via `effective.get(key, DEFAULT_...)`. Existing electricity entries load fine without migration.

### D7 — Aggregate sensors resolve per-tariff entity IDs via entity registry

The aggregate sensors call `_resolve_entity_id(hass, "sensor", UID_...)` to look up the live entity_id for each per-tariff sensor, exactly as `GasTotalCostSensor` does for `UID_GAS_PRICE_EUR`. This avoids hardcoding entity_id strings.

## Risks / Trade-offs

- **P1 meter entity name varies per user** — defaults are set to `sensor.energy_meter_energy_import_tariff_1` etc. (common dsmr/P1 integration naming). Users with different integrations must reconfigure. Mitigation: defaults are just defaults; all 4 are configurable.
- **Aggregate sensors depend on per-tariff sensors being registered** — if a per-tariff sensor is unavailable (e.g. meter not configured), the aggregate will be `None`/unavailable. Mitigation: treat any `None` per-tariff value as 0 in the aggregate compute to stay available.
- **`TOTAL_INCREASING` on aggregate sensors** — HA may warn if the derived value ever decreases (e.g. if a per-tariff sensor is reset). Mitigation: this is cosmetic; the aggregates follow the accumulators.
