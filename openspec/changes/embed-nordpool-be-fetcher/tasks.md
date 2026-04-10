## 1. Constants & config keys

- [ ] 1.1 Add `CONF_LOW_PRICE_CUTOFF` and `DEFAULT_LOW_PRICE_CUTOFF = 1.0` to `const.py`
- [ ] 1.2 Add `UID_ELECTRICITY_SPOT_CURRENT_PRICE` and `UID_ELECTRICITY_SPOT_AVERAGE_PRICE` to `const.py`
- [ ] 1.3 Add `SIGNAL_NORDPOOL_UPDATE` dispatcher signal constant to `const.py`
- [ ] 1.4 Add display names for spot sensors to `NAMES` dict in `const.py` (EN + NL)
- [ ] 1.5 Remove `DEFAULT_ELECTRICITY_PRICE_ENTITY` from `const.py`

## 2. Nord Pool BE store

- [ ] 2.1 Create `nordpool_store.py` with `NordpoolBeStore` class
- [ ] 2.2 Implement `async_fetch_today()` — GET `DayAheadPrices?currency=EUR&market=DayAhead&deliveryArea=BE&date=YYYY-MM-DD`, parse `multiAreaEntries` into `{"start": datetime, "end": datetime, "value": float}` slots (divide `entryPerArea["BE"]` by 10)
- [ ] 2.3 Implement `async_fetch_tomorrow()` — same fetch for tomorrow's date; sets `tomorrow_valid = True` when 96 slots returned
- [ ] 2.4 Implement `current_price` property — finds slot where `slot["start"] <= now() < slot["end"]` in `data_today`
- [ ] 2.5 Implement `average` property — `round(statistics.mean(...), 5)` over `data_today` values, `None` if empty
- [ ] 2.6 Implement `low_price` property — `current_price < average * low_price_cutoff`; `None` if either is `None`
- [ ] 2.7 Implement `price_percent_to_average` property — `round(current_price / average, 5)`; `None` if either is `None`
- [ ] 2.8 Implement `today` and `tomorrow` list properties (chronological `value` lists)
- [ ] 2.9 Implement `async_start(hass, low_price_cutoff)` — registers three time-change subscriptions (midnight refresh, 13:01 tomorrow fetch, `:X:01` 15-min tick) and runs initial fetch
- [ ] 2.10 Implement `_on_tick()` handler — updates `current_price`, dispatches `SIGNAL_NORDPOOL_UPDATE`; retries tomorrow fetch on ticks after 13:00 while `tomorrow_valid` is `False`
- [ ] 2.11 Implement `async_stop()` — unsubscribes all time-change listeners
- [ ] 2.12 Add error handling: catch HTTP errors and `KeyError`/`ValueError` on parse; log at ERROR level; leave cache unchanged; dispatch signal anyway so sensors go `unavailable`

## 3. `__init__.py` — store lifecycle & migration

- [ ] 3.1 Set `VERSION = 2` at module level (used by config entries)
- [ ] 3.2 Implement `async_migrate_entry`: for v1 electricity entries remove `current_price_entity`, `fx_rate_entity`, `unit` from data; bump to version 2. For v1 gas/settings entries just bump version. No-op for v2+.
- [ ] 3.3 In `async_setup_entry` for electricity entries: create `NordpoolBeStore`, call `async_start(hass, low_price_cutoff)`, store in `hass.data[DOMAIN]["nordpool_store"]`
- [ ] 3.4 In `async_unload_entry` for electricity entries: call `store.async_stop()`, remove from `hass.data[DOMAIN]`

## 4. Config flow — electricity setup & options

- [ ] 4.1 Remove `CONF_CURRENT_PRICE_ENTITY` and `CONF_FX_RATE_ENTITY` from `_electricity_schema()`
- [ ] 4.2 Remove `CONF_UNIT` (`vol.In(UNIT_OPTIONS)`) from `_electricity_schema()` — unit is always `c€/kWh`
- [ ] 4.3 Update default export template string in `_electricity_schema()` to reference `sensor.electricity_spot_average_price`
- [ ] 4.4 Add `CONF_LOW_PRICE_CUTOFF` (float, default `1.0`) to `_electricity_options_schema()` (options flow only, not setup)
- [ ] 4.5 Update `async_step_electricity_options` to save `low_price_cutoff` and reload the electricity entry so the store picks up the new cutoff

## 5. Sensor — spot sensor classes

- [ ] 5.1 Add `ElectricitySpotCurrentPriceSensor` class in `sensor.py` — subscribes to `SIGNAL_NORDPOOL_UPDATE`, reads `store.current_price`; state is `None` (unavailable) when store has no data
- [ ] 5.2 Add `extra_state_attributes` to `ElectricitySpotCurrentPriceSensor` — `today`, `tomorrow`, `tomorrow_valid`, `average`, `low_price`, `price_percent_to_average`
- [ ] 5.3 Add `ElectricitySpotAverageSensor` class in `sensor.py` — subscribes to `SIGNAL_NORDPOOL_UPDATE`, reads `store.average`
- [ ] 5.4 Register both spot sensors in `async_setup_entry` when `domain_type == DOMAIN_TYPE_ELECTRICITY`

## 6. Sensor — update import price sensor

- [ ] 6.1 Update `ElectricityImportPriceSensor` to track `sensor.electricity_spot_current_price` (internal entity) instead of reading `CONF_CURRENT_PRICE_ENTITY` from the config entry
- [ ] 6.2 Remove FX conversion and unit-detection logic from `ElectricityImportPriceSensor`
- [ ] 6.3 Remove `apply_fx` / `convert_unit` calls from the import price computation (formula is now `(spot + surcharge) * (1 + vat/100)` with all inputs in `c€/kWh`)

## 7. Cleanup

- [ ] 7.1 Remove `CONF_CURRENT_PRICE_ENTITY` and `CONF_FX_RATE_ENTITY` from the electricity branch of `async_setup_entry` in `sensor.py`
- [ ] 7.2 Remove `CONF_FX_RATE_ENTITY` import in `sensor.py` if no longer used (keep in `const.py` — still used by gas)
- [ ] 7.3 Remove `ElectricityImportPriceEurSensor` and `ElectricityExportPriceEurSensor` EUR bridge sensors if they were only needed due to the external entity unit mismatch (verify before removing)
- [ ] 7.4 Delete `DEFAULT_ELECTRICITY_PRICE_ENTITY` usage from all files
