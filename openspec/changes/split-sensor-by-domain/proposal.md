## Why

`sensor.py` is 1,535 lines containing 33 classes across three completely independent domains (electricity, gas, supplier). This violates the Single Responsibility Principle, makes the file hard to navigate, and will become increasingly problematic as each domain evolves separately — particularly as supplier entries grow to per-supplier files and the electricity entry is reworked in Phase 2 of the supplier spec.

## What Changes

- Extract `KrowiSensor` base class and `_resolve_entity_id` helper into `sensor_base.py`
- Extract all electricity-domain sensor classes into `sensor_electricity.py` (20 classes + `async_setup`)
- Extract all gas-domain sensor classes into `sensor_gas.py` (10 classes + `async_setup`)
- Extract all supplier-domain sensor classes into `sensor_supplier.py` (4 classes + `async_setup`)
- Reduce `sensor.py` to a thin router that delegates to each domain module via `async_setup_entry`
- No behavior changes — entity IDs, unique IDs, state, attributes, and signals are all unchanged

## Capabilities

### New Capabilities

_None. This is a structural refactor — no new entities, no new behavior._

### Modified Capabilities

_None. No spec-level requirements change. All existing specs remain valid against the refactored code._

## Impact

- **Modified**: `custom_components/krowi_energy_management/sensor.py` (reduced to router)
- **Created**: `sensor_base.py`, `sensor_electricity.py`, `sensor_gas.py`, `sensor_supplier.py`
- **Tests**: `tests/test_sensor.py` imports class names directly from `sensor` — imports will need updating in a follow-up refactor task (deferred, tests remain green via re-exports if needed)
- **No API changes**: HA platform entrypoint `sensor.py` is unchanged as a filename; `async_setup_entry` signature is unchanged
