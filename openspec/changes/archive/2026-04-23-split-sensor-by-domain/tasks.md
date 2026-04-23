## 1. Create new modules

- [x] 1.1 Create `sensor_base.py` with `KrowiSensor` base class and `_resolve_entity_id` helper (moved from `sensor.py`)
- [x] 1.2 Create `sensor_electricity.py` with all electricity sensor classes and `async_setup` function
- [x] 1.3 Create `sensor_gas.py` with all gas sensor classes and `async_setup` function
- [x] 1.4 Create `sensor_supplier.py` with all supplier sensor classes and `async_setup` function

## 2. Update router

- [x] 2.1 Replace `sensor.py` body with `async_setup_entry` routing to `sensor_electricity`, `sensor_gas`, `sensor_supplier`
- [x] 2.2 Remove all entity class definitions and domain logic from `sensor.py`

## 3. Verify

- [x] 3.1 Run full test suite (`pytest`) — all existing tests must pass
- [x] 3.2 Confirm no circular imports (`python -c "from custom_components.krowi_energy_management import sensor"`)

## 4. Follow-up (deferred)

- [x] 4.1 Update `tests/test_sensor.py` import paths to reference new module locations instead of `sensor`
