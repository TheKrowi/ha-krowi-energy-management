## Why

Users who have gas consumption data (via HomeWizard P1) and a computed gas price (EUR/kWh) currently have no way to track their cumulative gas spend directly in Home Assistant. A total cost sensor — accumulated by integrating raw m³ consumption against the live price and GCV — fills this gap without requiring external utility meter helpers or manual energy dashboard setup.

## What Changes

- Add a new `GasTotalCostSensor` entity to the gas config entry platform
- The sensor accumulates EUR cost incrementally: `Δm³ × GCV × price_EUR_per_kWh` on each meter tick
- Uses `RestoreEntity` to persist the accumulated total across HA restarts
- Reads raw m³ directly from the configured `gas_meter_entity` (bypasses the kWh derived sensor to avoid phantom GCV-change deltas)
- Guards against meter replacement (negative delta → re-anchor, no cost added) and meter unavailability (skip tick)
- Falls back to last known price if the price sensor is temporarily unavailable at tick time

## Capabilities

### New Capabilities

- `gas-total-cost`: Accumulated gas cost sensor in EUR, computed from raw m³ × GCV × EUR/kWh price, persisted via RestoreEntity, with meter-reset resilience

### Modified Capabilities

- `gas-sensors`: Add `gas_total_cost` entity to the gas sensor list

## Impact

- `sensor.py`: New `GasTotalCostSensor` class; registered in `async_setup_entry` for `DOMAIN_TYPE_GAS`
- `const.py`: New `UID_GAS_TOTAL_COST` constant and `NAMES` entries (EN + NL)
- `strings.json` / `translations/en.json` / `translations/nl.json`: No config flow changes needed — entity name is hardcoded via `NAMES`
