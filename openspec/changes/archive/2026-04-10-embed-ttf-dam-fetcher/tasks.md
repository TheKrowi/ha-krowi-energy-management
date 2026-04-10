## 1. Constants & config keys

- [x] 1.1 Add `UID_GAS_SPOT_TODAY_PRICE` and `UID_GAS_SPOT_AVERAGE_PRICE` to `const.py`
- [x] 1.2 Add `SIGNAL_TTF_DAM_UPDATE` dispatcher signal constant to `const.py`
- [x] 1.3 Add display names for gas spot sensors to `NAMES` dict in `const.py` (EN + NL keys)
- [x] 1.4 Add `GAS_UNIT = "c€/kWh"` hardcoded constant to `const.py`
- [x] 1.5 Remove `CONF_CURRENT_PRICE_ENTITY` from `const.py` (gas was its last consumer)
- [x] 1.6 Remove gas-specific `CONF_UNIT` or `DEFAULT_GAS_PRICE_ENTITY` from `const.py` (if still present)

## 2. TTF DAM store

- [x] 2.1 Create `ttf_dam_store.py` with `TtfDamStore` class
- [x] 2.2 Implement `async_fetch()` — GET `https://mijn.elindus.be/marketinfo/dayahead/prices?from=YYYY-MM-DD&to=YYYY-MM-DD&market=GAS&granularity=DAY`; `from = (today - 30d).isoformat()`, `to = today.isoformat()`
- [x] 2.3 In `async_fetch()`: parse `response["statistics"]["averagePrice"] / 10` → `_average` (c€/kWh)
- [x] 2.4 In `async_fetch()`: sort `response["dataSeries"]["data"]` by `x`; take last entry; `last["y"] / 10` → `_today_price` (c€/kWh)
- [x] 2.5 In `async_fetch()`: compare date of last entry (parse `last["x"]` as Unix ms to `date`) against `date.today()`; set `_data_is_fresh` accordingly
- [x] 2.6 In `async_fetch()`: dispatch `SIGNAL_TTF_DAM_UPDATE` via `async_dispatcher_send` regardless of freshness
- [x] 2.7 Add error handling: catch HTTP errors, `KeyError`, `ValueError`; log at ERROR; leave cache unchanged; dispatch signal anyway so sensors go `unavailable`
- [x] 2.8 Implement `today_price: float | None` and `average: float | None` properties
- [x] 2.9 Implement `data_is_fresh: bool` property
- [x] 2.10 Implement `async_start(hass)` — immediately call `async_fetch()`; subscribe to midnight tick `(hour=0, minute=0, second=1)`; subscribe to 30-min ticks `(minute=[0, 30], second=1)` for retry loop
- [x] 2.11 Implement midnight handler — set `_data_is_fresh = False`, call `async_fetch()`
- [x] 2.12 Implement 30-min tick handler — if `_data_is_fresh` is False, call `async_fetch()`; else no-op
- [x] 2.13 Implement `async_stop()` — call each stored unsubscribe callable

## 3. `__init__.py` — store lifecycle & migration

- [x] 3.1 Set `VERSION = 3` at module level
- [x] 3.2 Update `async_migrate_entry`: for gas v2 entries remove `unit` and `current_price_entity` from data, set version 3; for electricity/settings v2 entries just set version 3; no-op for v3+
- [x] 3.3 In `async_setup_entry` for gas entries: create `TtfDamStore`, call `async_start(hass)`, store in `hass.data[DOMAIN]["ttf_dam_store"]`
- [x] 3.4 In `async_unload_entry` for gas entries: call `store.async_stop()`, remove from `hass.data[DOMAIN]`

## 4. Config flow — gas setup simplified

- [x] 4.1 Remove `CONF_CURRENT_PRICE_ENTITY` from `_gas_schema()` (and any related default entity constant)
- [x] 4.2 Remove `CONF_UNIT` (gas unit selector `vol.In(UNIT_OPTIONS)`) from `_gas_schema()`
- [x] 4.3 Update `async_step_gas` / `async_step_gas_options` to no longer process `unit` or `current_price_entity`
- [x] 4.4 Ensure gas config entry data on fresh setup contains only `domain_type = "gas"` (no other fields required at setup time)

## 5. Sensor — gas spot sensor classes

- [x] 5.1 Add `GasSpotTodayPriceSensor` class in `sensor.py` — subscribes to `SIGNAL_TTF_DAM_UPDATE`; reads `store.today_price`; state is `None` (unavailable) when store has no fresh data
- [x] 5.2 Set `unit_of_measurement = "c€/kWh"`, `state_class = SensorStateClass.MEASUREMENT`, `device_class = None` on `GasSpotTodayPriceSensor`
- [x] 5.3 Add `GasSpotAverageSensor` class in `sensor.py` — subscribes to `SIGNAL_TTF_DAM_UPDATE`; reads `store.average`
- [x] 5.4 Set `unit_of_measurement = "c€/kWh"`, `state_class = SensorStateClass.MEASUREMENT` on `GasSpotAverageSensor`
- [x] 5.5 Register both spot sensors in `async_setup_entry` when `domain_type == DOMAIN_TYPE_GAS`

## 6. Sensor — update gas current price sensor

- [x] 6.1 Update `GasCurrentPriceSensor` to track `sensor.gas_spot_today_price` (internal entity) instead of reading `CONF_CURRENT_PRICE_ENTITY` from the config entry
- [x] 6.2 Remove unit auto-conversion and external entity unit detection logic from `GasCurrentPriceSensor`
- [x] 6.3 Formula is now `(gas_spot_today_price + surcharge) * (1 + vat/100)` with all inputs in `c€/kWh`
- [x] 6.4 Mark state `unavailable` when `gas_spot_today_price` is `unavailable` or `unknown`

## 7. `number.py` — gas unit hardcoded

- [x] 7.1 Update gas tariff `NumberEntity` classes to use `GAS_UNIT` constant (`"c€/kWh"`) instead of reading `unit` from the config entry
- [x] 7.2 Confirm gas VAT entity still uses `"%" ` unit unchanged

## 8. Cleanup

- [x] 8.1 Remove `CONF_CURRENT_PRICE_ENTITY` import everywhere (no remaining usage after steps above)
- [x] 8.2 Remove any reference to gas `unit` from `sensor.py` (e.g. in `GasCurrentPriceSensor` init, `gas_eur_sensors`)
- [x] 8.3 Update `gas_current_price_eur` bridge sensor to always use divide-by-100 (c€/kWh → EUR/kWh), removing the unit-conditional branching
- [x] 8.4 Verify no other code reads `entry.data["unit"]` for gas entries before finalising migration
