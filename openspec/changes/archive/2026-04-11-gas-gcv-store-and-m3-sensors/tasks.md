## 1. Constants and config keys

- [x] 1.1 Add `CONF_GOS_ZONE`, `DEFAULT_GOS_ZONE`, `CONF_GAS_METER_ENTITY`, `DEFAULT_GAS_METER_ENTITY` to `const.py`
- [x] 1.2 Add `ATRIAS_GCV_API_URL`, `ATRIAS_SUBSCRIPTION_KEY` to `const.py`
- [x] 1.3 Add `SIGNAL_GCV_UPDATE` dispatcher constant to `const.py`
- [x] 1.4 Add UID suffixes `UID_GAS_CALORIFIC_VALUE`, `UID_GAS_PRICE_M3`, `UID_GAS_CONSUMPTION_KWH` to `const.py`
- [x] 1.5 Add `GOS_ZONE_OPTIONS` list (all ~60 Belgian GOS zone names, alphabetically sorted) to `const.py`
- [x] 1.6 Add display name entries for new sensors to `NAMES` dict in `const.py` (EN + NL for each)

## 2. GcvStore implementation

- [x] 2.1 Create `gcv_store.py` with `GcvStore` class skeleton (init, `async_start`, `async_stop`, properties `gcv`, `history`, `data_is_fresh`)
- [x] 2.2 Implement `async_fetch(year, month)` — HTTP GET Atrias URL, parse CSV, extract GCV for configured zone, handle 404 gracefully
- [x] 2.3 Implement gap-fill bootstrap loop in `async_start`: compute 12 target months, find missing ones, fetch oldest-first
- [x] 2.4 Implement HA storage persistence (`hass.helpers.storage.Store`) — load on start, save after each successful fetch, prune to 12 entries
- [x] 2.5 Implement `data_is_fresh` flag: set `True` after most-recent target month is fetched, `False` on 1st of month
- [x] 2.6 Subscribe `async_track_time_change(hour=6, minute=0, second=1)` for daily retry when `data_is_fresh` is `False`
- [x] 2.7 Subscribe `async_track_time_change(hour=0, minute=0, second=1, day=1)` for 1st-of-month reset and immediate re-fetch
- [x] 2.8 Dispatch `SIGNAL_GCV_UPDATE` after every successful fetch

## 3. Config and options flow

- [x] 3.1 Add `CONF_GOS_ZONE` dropdown (using `GOS_ZONE_OPTIONS`, default `DEFAULT_GOS_ZONE`) to gas options flow schema
- [x] 3.2 Add `CONF_GAS_METER_ENTITY` `EntitySelector()` field (default `DEFAULT_GAS_METER_ENTITY`) to gas options flow schema
- [x] 3.3 Ensure `effective` dict in `async_setup_entry` reads both new keys from options with defaults

## 4. GcvStore lifecycle wiring in __init__.py

- [x] 4.1 Instantiate `GcvStore` in gas `async_setup_entry`, passing `CONF_GOS_ZONE` from effective config
- [x] 4.2 Call `await store.async_start(hass)` after instantiation
- [x] 4.3 Store instance in `hass.data[DOMAIN]["gcv_store"]`
- [x] 4.4 Call `store.async_stop()` and remove from `hass.data` in gas `async_unload_entry`

## 5. New sensor entities

- [x] 5.1 Implement `GasCalorificValueSensor` — subscribes to `SIGNAL_GCV_UPDATE`, reads `store.gcv`, exposes `history` and `data_is_fresh` as extra state attributes
- [x] 5.2 Implement `GasCurrentPriceM3Sensor` — tracks state changes on `gas_current_price_eur`, reads `store.gcv`, computes `eur_kwh × gcv` rounded to 5 dp
- [x] 5.3 Implement `GasConsumptionKwhSensor` — tracks state changes on `CONF_GAS_METER_ENTITY`, reads `store.gcv`, computes `m3 × gcv` rounded to 3 dp, `state_class = total_increasing`, `device_class = energy`
- [x] 5.4 All three sensors: guard for `None` meter entity, unavailable/unknown states, and `None` GCV → return `None` native value
- [x] 5.5 Register all three sensors under Gas device (`(DOMAIN, entry_id + "_gas")`)
- [x] 5.6 Add all three sensors to the gas platform setup in `sensor.py`

## 6. Strings and translations

- [x] 6.1 Add `CONF_GOS_ZONE` and `CONF_GAS_METER_ENTITY` labels/descriptions to `strings.json` options flow section
- [x] 6.2 Update `translations/en.json` with new options flow field labels
- [x] 6.3 Update `translations/nl.json` with Dutch translations for new options flow fields
