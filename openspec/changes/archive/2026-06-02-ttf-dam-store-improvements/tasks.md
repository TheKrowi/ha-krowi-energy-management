## 1. Constants & strings

- [x] 1.1 Add `UID_GAS_SPOT_MONTH_AVERAGE_PRICE = "gas_spot_month_average_price"` to `const.py`
- [x] 1.2 Add EN display name `"Monthly average price MTD (TTF DAM)"` to `NAMES` dict in `const.py`
- [x] 1.3 Add NL display name `"Maandgemiddelde t/m vandaag (TTF DAM)"` to `NAMES` dict in `const.py`
- [x] 1.4 Add `gas_spot_month_average_price` string entry to `strings.json` and both translation files (`en.json`, `nl.json`)

## 2. TtfDamStore — buffer persistence

- [x] 2.1 Add `_daily_buffer: dict[date, float] = {}` instance field
- [x] 2.2 Add `_fetch_in_flight: bool = False` instance field
- [x] 2.3 Implement `_async_load_buffer(hass)` — open HA `Store("krowi_energy_management_ttf_dam_daily", 1)`; read stored dict; populate `_daily_buffer` via `date.fromisoformat(k): v` for each entry
- [x] 2.4 Implement `_trim_buffer()` — drop all keys where `d < dt_utils.now().date() - relativedelta(months=1)`
- [x] 2.5 Implement `_save_buffer(hass)` — schedule fire-and-forget `hass.async_create_task(store.async_save({d.isoformat(): v ...}))` (mirror NordpoolBeStore pattern)
- [x] 2.6 In `async_start(hass)`: call `await self._async_load_buffer(hass)`, then `self._trim_buffer()`, then `self._save_buffer(hass)` before the initial `async_fetch()`

## 3. TtfDamStore — fetch rewrite

- [x] 3.1 In `async_fetch()`: add guard `if self._fetch_in_flight: return` at top; set `self._fetch_in_flight = True`; wrap fetch body in `try/finally` that sets `self._fetch_in_flight = False`
- [x] 3.2 Replace `from_date = (date.today() - timedelta(days=30))` with `from_date = dt_utils.now().date() - relativedelta(months=1)`
- [x] 3.3 Replace `to_date = date.today()` with `to_date = dt_utils.now().date()`
- [x] 3.4 Remove read of `data["statistics"]["averagePrice"]`; remove `self._average = ...` assignment from the API response
- [x] 3.5 Iterate all `data["dataSeries"]["data"]` entries; for each entry compute `local_date = dt_utils.as_local(datetime.fromtimestamp(entry["x"] / 1000, tz=timezone.utc)).date()` and `value = entry["y"] / 10`; write `self._daily_buffer[local_date] = value`
- [x] 3.6 After merging: call `self._trim_buffer()` then `self._save_buffer(hass)`
- [x] 3.7 Remove `self._today_price = ...` assignment; remove `self._data_is_fresh = ...` assignment based on last entry date comparison
- [x] 3.8 Signal dispatch: keep `async_dispatcher_send(hass, SIGNAL_TTF_DAM_UPDATE)` after buffer save

## 4. TtfDamStore — properties rewrite

- [x] 4.1 Remove `today_price: float | None` property (backed by deleted `_today_price`); replace with property that returns `self._daily_buffer.get(dt_utils.now().date())`
- [x] 4.2 Remove `average: float | None` property backed by deleted `_average`; replace with `rolling_average: float | None` property — `mean(v for d, v in self._daily_buffer.items() if d >= cutoff)` where cutoff = `dt_utils.now().date() - relativedelta(months=1)`; return `None` if buffer is empty
- [x] 4.3 Add `month_average: float | None` property — `mean(v for d, v in self._daily_buffer.items() if d >= dt_utils.now().date().replace(day=1))`; return `None` if no entries yet
- [x] 4.4 Update `data_is_fresh: bool` property — return `dt_utils.now().date() in self._daily_buffer`

## 5. TtfDamStore — midnight handler fix

- [x] 5.1 In `_on_midnight` handler: add guard `if self._fetch_in_flight: return` after any necessary reset
- [x] 5.2 Keep `_data_is_fresh` reset removed from midnight — freshness now derived from buffer, so no explicit reset field needed (the day's key won't exist in the buffer at midnight until the fetch populates it)
- [x] 5.3 In `_on_tick` handler: guard is already covered by `_fetch_in_flight` check in `async_fetch()`; ensure handler calls `async_fetch()` only when not already in flight (rely on 3.1 guard)

## 6. sensor_gas.py — new sensor + updated properties

- [x] 6.1 Add `GasSpotMonthAveragePriceSensor` class — subscribes to `SIGNAL_TTF_DAM_UPDATE`; reads `store.month_average`; state is `None` (unavailable) when `month_average` is `None`; `unit_of_measurement = "c€/kWh"`; `state_class = SensorStateClass.MEASUREMENT`; `device_class = None`; UID = `UID_GAS_SPOT_MONTH_AVERAGE_PRICE`
- [x] 6.2 Update `GasSpotAveragePriceSensor` — change property read from `store.average` to `store.rolling_average`
- [x] 6.3 Update `GasSpotTodayPriceSensor` — change property read from `store.today_price` to `store.today_price` (property rename in 4.1 is transparent if kept as `today_price`; verify rename is consistent)
- [x] 6.4 Register `GasSpotMonthAveragePriceSensor` in `async_setup_entry` alongside the existing two spot sensors

## 7. Tests

- [x] 7.1 Update `test_ttf_dam_store.py`: replace tests asserting `store.today_price` from `_today_price` with buffer-based assertions
- [x] 7.2 Update `test_ttf_dam_store.py`: replace `store.average` assertions with `store.rolling_average` assertions
- [x] 7.3 Add tests for `store.month_average`: one entry (first of month), multiple entries spanning month boundary, empty buffer
- [x] 7.4 Add test: `_fetch_in_flight` guard prevents double fetch at midnight
- [x] 7.5 Add test: buffer persists across simulated restart (load from Storage mock)
- [x] 7.6 Add test: `data_is_fresh` is `True` when today's local date is in buffer, `False` otherwise
- [x] 7.7 Add test: Unix ms timestamp → local date conversion is correct for Europe/Brussels timezone (near midnight, UTC date differs)
