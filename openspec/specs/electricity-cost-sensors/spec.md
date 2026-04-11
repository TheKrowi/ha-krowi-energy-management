# Spec: electricity-cost-sensors

## Purpose

Defines the electricity cost accumulator sensors that track monetary cost and revenue over time by multiplying P1 meter deltas against configured price entities, plus derived total and net-cost sensors.

## Requirements

### Requirement: Four per-tariff electricity cost accumulator sensors
The component SHALL create four `RestoreEntity` sensor instances for the electricity domain that accumulate monetary cost/revenue over time.

| Unique ID | Friendly name (EN) | state_class | unit |
|-----------|-------------------|-------------|------|
| `electricity_import_cost_tariff_1` | Import cost (tariff 1) | TOTAL_INCREASING | EUR |
| `electricity_import_cost_tariff_2` | Import cost (tariff 2) | TOTAL_INCREASING | EUR |
| `electricity_export_revenue_tariff_1` | Export revenue (tariff 1) | TOTAL_INCREASING | EUR |
| `electricity_export_revenue_tariff_2` | Export revenue (tariff 2) | TOTAL_INCREASING | EUR |

Each sensor SHALL:
- Subscribe to state-change events on its configured meter entity.
- Compute `delta_kwh = new_kwh − last_kwh` on each tick.
- Add `delta_kwh × price_EUR_per_kWh` to the running total.
- Store the running total and restore it via `RestoreEntity` across HA restarts.
- Treat the configured price entity's state as already in EUR/kWh (no internal conversion).

#### Scenario: Normal accumulation tick
- **WHEN** the configured meter entity's state increases by `Δkwh`
- **THEN** the sensor's value SHALL increase by `Δkwh × price_EUR_per_kWh` (rounded to 5 decimal places)
- **THEN** `_last_kwh` SHALL be updated to the new meter reading

#### Scenario: First reading anchors without accumulating
- **WHEN** the sensor loads and reads the meter for the first time (no prior `_last_kwh`)
- **THEN** `_last_kwh` SHALL be set to the current meter value
- **THEN** no cost SHALL be added to the total

#### Scenario: Negative delta — meter replaced or P1 glitch
- **WHEN** the meter reading decreases (new value < last value)
- **THEN** `_last_kwh` SHALL be updated to the new reading
- **THEN** the accumulated total SHALL remain unchanged

#### Scenario: Zero delta — no consumption
- **WHEN** the meter reading is the same as the last reading
- **THEN** the accumulated total SHALL remain unchanged

#### Scenario: Price entity unavailable — use last known price
- **WHEN** the price entity is unavailable or returns a non-numeric state on a tick where delta > 0
- **AND** a previously valid price has been seen
- **THEN** the last known price SHALL be used for the cost increment

#### Scenario: Price entity never seen — skip tick
- **WHEN** the price entity has never returned a valid numeric state
- **AND** delta > 0
- **THEN** the tick SHALL be skipped (no cost added, `_last_kwh` not updated)

#### Scenario: Accumulated total restored after HA restart
- **WHEN** HA restarts and the sensor loads
- **THEN** the sensor SHALL restore its previously accumulated total via `RestoreEntity`
- **THEN** accumulation SHALL resume from that restored total

#### Scenario: Meter entity not configured
- **WHEN** no meter entity is configured for a tariff
- **THEN** the sensor SHALL be unavailable

---

### Requirement: Two derived electricity total sensors
The component SHALL create two derived sensor instances that sum the per-tariff accumulators.

| Unique ID | Friendly name (EN) | Formula | state_class | unit |
|-----------|-------------------|---------|-------------|------|
| `electricity_total_import_cost` | Total import cost | import_T1 + import_T2 | TOTAL_INCREASING | EUR |
| `electricity_total_export_revenue` | Total export revenue | export_T1 + export_T2 | TOTAL_INCREASING | EUR |

These sensors SHALL:
- Subscribe to state-change events on the 4 per-tariff sensor entities.
- Recompute their value whenever any of the tracked sensors change.
- Treat a `None`/unavailable per-tariff sensor value as `0` when computing the sum.
- Have no own accumulator state — they are purely derived.

#### Scenario: Both per-tariff sensors available
- **WHEN** both per-tariff sensors have valid numeric states
- **THEN** the total sensor SHALL equal their sum (rounded to 5 decimal places)

#### Scenario: One per-tariff sensor unavailable
- **WHEN** one per-tariff sensor is unavailable and the other has a valid state
- **THEN** the total sensor SHALL treat the unavailable one as 0 and remain available

#### Scenario: Both per-tariff sensors unavailable
- **WHEN** both per-tariff sensors are unavailable
- **THEN** the total sensor SHALL be unavailable

#### Scenario: Updates reactively on per-tariff change
- **WHEN** a per-tariff sensor's value changes
- **THEN** the total sensor SHALL recompute and update within the same HA event loop cycle

---

### Requirement: Electricity net cost sensor
The component SHALL create one derived sensor that computes the net electricity cost.

| Unique ID | Friendly name (EN) | Formula | state_class | unit |
|-----------|-------------------|---------|-------------|------|
| `electricity_net_cost` | Net electricity cost | total_import_cost − total_export_revenue | MEASUREMENT | EUR |

This sensor SHALL:
- Subscribe to state-change events on `electricity_total_import_cost` and `electricity_total_export_revenue`.
- Recompute on every change.
- Allow negative values (when export revenue exceeds import cost).
- Have no own accumulator state.

#### Scenario: Import exceeds export
- **WHEN** total import cost > total export revenue
- **THEN** net cost SHALL be positive

#### Scenario: Export exceeds import
- **WHEN** total export revenue > total import cost
- **THEN** net cost SHALL be negative

#### Scenario: Either total sensor unavailable
- **WHEN** either total sensor is unavailable
- **THEN** net cost SHALL be unavailable
