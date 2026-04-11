# Spec: gas-total-cost

## Purpose

Defines the accumulated gas total cost sensor in EUR.

## Requirements

### Requirement: Gas total cost sensor
The component SHALL expose a sensor with unique ID `gas_total_cost` and English display name "Total gas cost" that accumulates the total gas expenditure in EUR since the sensor was first created (or last reset via HA Storage clear).

The sensor SHALL use `state_class = TOTAL_INCREASING`, `device_class = SensorDeviceClass.MONETARY`, and `unit_of_measurement = "EUR"`.

Accumulation formula per meter tick: `Δm³ × gcv × price_EUR_per_kWh`

Where:
- `Δm³ = new_m3 - _last_m3` (raw cubic meters from the configured `gas_meter_entity`)
- `gcv` is the current calorific value from `GcvStore` (kWh/m³)
- `price_EUR_per_kWh` is the current value of `gas_current_price_eur`

Value SHALL be rounded to 5 decimal places.

The sensor SHALL persist `total_cost` across HA restarts using `RestoreEntity`. On startup, `_last_m3` SHALL be re-anchored to the current meter reading (no attempt to cost the restart gap). The accumulated total SHALL be restored from the previous persisted state.

#### Scenario: Normal accumulation
- **WHEN** `gas_meter_entity` state increases from 100.0 m³ to 100.5 m³
- **AND** GCV is 10.5 kWh/m³
- **AND** `gas_current_price_eur` is 0.062 EUR/kWh
- **THEN** `gas_total_cost` SHALL increase by `0.5 × 10.5 × 0.062 = 0.32550` EUR

#### Scenario: Meter replacement — negative delta is ignored
- **WHEN** `gas_meter_entity` state drops from 50000.0 m³ to 0.0 m³
- **THEN** `gas_total_cost` SHALL NOT change
- **AND** `_last_m3` SHALL be re-anchored to `0.0`
- **AND** subsequent positive deltas SHALL accumulate normally from the new anchor

#### Scenario: Meter unavailable — tick is skipped
- **WHEN** `gas_meter_entity` state becomes `unavailable` or `unknown`
- **THEN** `gas_total_cost` SHALL NOT change
- **AND** `_last_m3` SHALL NOT be updated

#### Scenario: Price temporarily unavailable — use last known price
- **WHEN** `gas_current_price_eur` is `unavailable` at tick time
- **AND** a valid price was seen previously in this session
- **THEN** the sensor SHALL use the last known price to compute the cost increment
- **AND** accumulation SHALL NOT be skipped

#### Scenario: Price unavailable with no prior known price — skip tick
- **WHEN** `gas_current_price_eur` is `unavailable` at tick time
- **AND** no valid price has been seen in this session yet
- **THEN** `gas_total_cost` SHALL NOT change for that tick

#### Scenario: GCV unavailable — skip tick
- **WHEN** `GcvStore.gcv` is `None` at tick time
- **THEN** `gas_total_cost` SHALL NOT change for that tick

#### Scenario: Persistence across restart
- **WHEN** HA restarts with `gas_total_cost` previously at `€285.50`
- **THEN** `gas_total_cost` SHALL restore to `285.50` after startup
- **AND** accumulation SHALL continue from that value

#### Scenario: Fresh install — starts at zero
- **WHEN** the gas config entry is set up for the first time and no prior state exists
- **THEN** `gas_total_cost` SHALL start at `0.0`
