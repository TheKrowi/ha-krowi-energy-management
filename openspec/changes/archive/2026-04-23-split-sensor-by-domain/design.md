## Context

`sensor.py` is 1,535 lines containing 33 classes across three independent domains: electricity (market + grid costs + legacy price sensors + cost accumulators), gas, and supplier. All domain logic, the base class, and the HA platform entrypoint co-exist in one file.

This is a pure structural refactor — no behavior, entity IDs, unique IDs, or state changes.

## Goals / Non-Goals

**Goals:**
- One file per domain: `sensor_electricity.py`, `sensor_gas.py`, `sensor_supplier.py`
- Shared base extracted to `sensor_base.py`
- `sensor.py` reduced to a routing-only entrypoint (no entity class definitions)
- No circular imports
- All existing tests pass without modification

**Non-Goals:**
- Changing any entity behavior, formula, attribute, or unique ID
- Refactoring `_ElectricityTariffCostSensor` or `GasTotalCostSensor` accumulator pattern
- Adding a `_track_dispatcher` helper to `KrowiSensor` (can follow separately)
- Updating `test_sensor.py` import paths (deferred task)
- Phase 2 supplier proxy sensors (tracked in `supplier-price-sensors` spec)

## Decisions

### D1 — `sensor_base.py` holds `KrowiSensor` and `_resolve_entity_id`

`_resolve_entity_id` is used by all three domain files. It belongs alongside the base class rather than in `utils.py`, because it depends on the entity registry (a HA-specific concern), whereas `utils.py` contains pure computation functions. All three domain files import from `sensor_base`, not from each other.

_Alternative considered_: put `_resolve_entity_id` in `utils.py`. Rejected: breaks the purity of `utils.py` and adds a HA framework import to an otherwise framework-free module.

### D2 — Each domain module exposes an `async_setup` function (not `async_setup_entry`)

Domain modules expose:
```python
async def async_setup(hass, entry, async_add_entities) -> None: ...
```

`sensor.py` remains the HA platform entrypoint with `async_setup_entry`, which delegates:
```python
async def async_setup_entry(hass, entry, async_add_entities):
    domain_type = entry.data[CONF_DOMAIN_TYPE]
    if domain_type == DOMAIN_TYPE_ELECTRICITY:
        await sensor_electricity.async_setup(hass, entry, async_add_entities)
    elif domain_type == DOMAIN_TYPE_GAS:
        await sensor_gas.async_setup(hass, entry, async_add_entities)
    elif domain_type == DOMAIN_TYPE_ELECTRICITY_SUPPLIER:
        await sensor_supplier.async_setup(hass, entry, async_add_entities)
```

HA never calls domain modules directly — only `sensor.py` is the registered platform.

_Alternative considered_: move `async_setup_entry` into each domain module and have `sensor.py` re-export them. Rejected: HA requires exactly one `async_setup_entry` in the platform file; re-exporting creates ambiguity.

### D3 — No re-exports from `sensor.py`

`sensor.py` will not re-export class names (e.g. `from .sensor_electricity import *`). Tests that import class names directly from `sensor` will need their imports updated in a follow-up task. This is acceptable because the tests are unit tests that can be updated independently and the refactor itself is not breaking at runtime.

_Alternative considered_: add `__all__` re-exports to keep tests green immediately. Rejected: re-exports defeat the purpose of the split and add maintenance burden.

### D4 — Module dependency graph

```
sensor_base.py
    ↑
    ├── sensor_electricity.py  (imports KrowiSensor, _resolve_entity_id from sensor_base)
    ├── sensor_gas.py          (imports KrowiSensor, _resolve_entity_id from sensor_base)
    └── sensor_supplier.py     (imports KrowiSensor, _resolve_entity_id from sensor_base)

sensor.py (router)
    imports: sensor_electricity, sensor_gas, sensor_supplier, const (CONF_DOMAIN_TYPE, DOMAIN_TYPE_*)
    does NOT import: any entity classes directly
```

No circular imports. Domain files never import from each other.

## Risks / Trade-offs

- [Risk] `test_sensor.py` imports entity classes directly from `sensor` → class not found after split  
  Mitigation: Defer test import updates to a follow-up task; note in tasks.md. Tests can be temporarily skipped for affected classes with a `# TODO` marker if they fail CI.

- [Risk] `_ElectricityTariffCostSensor` is a private base class used only within electricity — it moves to `sensor_electricity.py` cleanly, but if future gas or supplier sensors need a similar accumulator pattern, there will be duplication.  
  Mitigation: Accept the duplication now; extracting a shared `_AccumulatorSensor` to `sensor_base.py` is a separate, well-bounded future task.

## Migration Plan

1. Create `sensor_base.py` with `KrowiSensor` and `_resolve_entity_id`
2. Create `sensor_electricity.py` with all electricity classes + `async_setup`
3. Create `sensor_gas.py` with all gas classes + `async_setup`
4. Create `sensor_supplier.py` with all supplier classes + `async_setup`
5. Replace `sensor.py` body with the router + necessary imports only
6. Run full test suite — all existing tests should pass (module-level imports in `test_sensor.py` may need updating)
7. Manual smoke-test: confirm HA loads entities without errors on all three domain types
