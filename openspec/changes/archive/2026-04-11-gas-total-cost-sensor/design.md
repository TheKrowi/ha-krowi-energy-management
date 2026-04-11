## Context

The gas sensor platform already computes `gas_current_price_eur` (EUR/kWh) and `gas_consumption_kwh` (derived from a raw m³ HomeWizard meter × GCV). Users need a single accumulating EUR value they can use in dashboards, automations, or cost-tracking without configuring a Utility Meter helper.

The key constraint is that `gas_consumption_kwh` is derived via multiplication with GCV, which updates monthly. Using it as the accumulation source would cause phantom cost deltas whenever GCV is refreshed. The raw m³ meter entity (`gas_meter_entity`, a HomeWizard external device exposed via DSMR on P1) is the correct accumulation trigger.

## Goals / Non-Goals

**Goals:**
- Accumulate `Δm³ × GCV × price_EUR_kWh` on every meter tick into a persistent EUR total
- Survive HA restarts without losing the accumulated total (RestoreEntity)
- Handle meter replacement (negative delta) and meter unavailability gracefully
- Cache last known price so a brief price-sensor outage does not skip cost accumulation

**Non-Goals:**
- Daily/monthly windowing — that is HA's long-term statistics responsibility
- Resetting or zeroing the counter from the UI
- Handling meters that report in units other than m³

## Decisions

### Track raw m³, not derived kWh

**Decision**: `GasTotalCostSensor` watches `gas_meter_entity` directly (same entity `GasConsumptionKwhSensor` uses) and multiplies `Δm³ × gcv_store.gcv × price`.

**Why over watching `gas_consumption_kwh`**: GCV updates happen monthly. If the sensor watched the kWh sensor, a GCV refresh triggers a state change with no actual gas consumed — producing a phantom cost increment. By watching raw m³ and reading GCV in-process, GCV changes are invisible to the accumulator.

**Alternatives considered**: Re-anchor `_last_kwh` on `SIGNAL_GCV_UPDATE` (Option B) — achieves the same correctness but adds a second listener and more complex logic for no additional benefit.

### RestoreEntity for persistence

**Decision**: `GasTotalCostSensor` inherits from both `KrowiSensor` and `RestoreEntity`. In `async_added_to_hass`, restore the previous `native_value` from HA's state machine storage before anchoring `_last_m3`.

**Why**: Consistent with `KrowiNumberEntity` in `number.py`, which already uses `RestoreNumber`. No coordinator or DB write is required — HA handles the storage automatically when `write_ha_state()` is called.

**Note**: `_last_m3` is NOT persisted — it is re-anchored to the current meter reading on every startup. This is intentional: the gap during a restart is immeasurable and should not be costed.

### Negative delta = meter replaced, re-anchor and skip

**Decision**: If `new_m3 < _last_m3`, treat it as a meter replacement: set `_last_m3 = new_m3`, add no cost, continue.

**Why**: The HomeWizard gas entity is `TOTAL_INCREASING` with `SensorDeviceClass.GAS`. A backward jump can only mean a meter reset. The consumption during the gap is unrecoverable; the honest response is to accept the gap silently.

### Cache last known price

**Decision**: Store `_last_known_price: float | None` in the sensor. On each tick, attempt to read the current price; if unavailable, fall back to `_last_known_price`. If neither is available, skip the tick entirely.

**Why**: TTF DAM prices are stable over hours. A brief unavailability of `gas_current_price_eur` (e.g., API timeout, HA startup sequencing) should not cause a consumption tick to be dropped silently. Using the last known price is a better approximation than skipping.

## Risks / Trade-offs

- **Restart gap undercount**: Gas consumed during an HA restart is not costed. This is unavoidable without a separate persistent m³ checkpoint. For typical restarts (seconds to minutes), the monetary impact is negligible.
- **Rate change between ticks**: Gas price updates daily (TTF DAM). If the price changes between two meter ticks (5-minute interval), the tick uses whichever price was current at the moment of the tick. This is the standard left-Riemann-sum approximation and is accurate enough for billing estimation.
- **First startup with no prior state**: On fresh install, `_total_cost` starts at `0.0` and `_last_m3` is anchored to the current meter reading. No historical cost is recovered — this is expected and documented.
