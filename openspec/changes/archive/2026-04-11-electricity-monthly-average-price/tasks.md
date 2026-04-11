## 1. NordpoolBeStore — Buffer & Persistence

- [x] 1.1 Add `_daily_avg_buffer: dict[date, float]` field to `NordpoolBeStore.__init__`
- [x] 1.2 Add `_storage: Store | None` field and import `homeassistant.helpers.storage.Store`
- [x] 1.3 Implement `async _async_load_buffer()`: load from storage, parse ISO-string keys back to `date`, default to `{}` on missing/corrupt file
- [x] 1.4 Implement `_save_buffer()`: serialise `_daily_avg_buffer` to `{"YYYY-MM-DD": float}` and call `self._storage.async_save()`
- [x] 1.5 Implement `_trim_buffer()`: drop entries where `date < date.today() - relativedelta(months=1)`
- [x] 1.6 Add `monthly_average` property: `round(mean([*_daily_avg_buffer.values(), self.average]), 5)`; return `None` if `self.average is None`; return `round(self.average, 5)` if buffer empty

## 2. NordpoolBeStore — Backfill

- [x] 2.1 Implement `async _async_backfill()`: compute required date set `[today - relativedelta(months=1), yesterday]`, diff against buffer keys, fetch each missing date via `_async_fetch(date_str)`, compute mean from returned slots, insert into buffer; skip silently on fetch failure
- [x] 2.2 Call `_async_backfill()` in `async_start` after loading buffer and after `async_fetch_today()`, before dispatching `SIGNAL_NORDPOOL_UPDATE`

## 3. NordpoolBeStore — Midnight Snapshot

- [x] 3.1 Implement `_snapshot_today()`: read `self.average`, if not `None` write to `_daily_avg_buffer[date.today() - timedelta(days=1)]`, call `_trim_buffer()`, call `_save_buffer()`
- [x] 3.2 Update `_on_midnight` to call `_snapshot_today()` BEFORE `async_fetch_today()`

## 4. const.py — Display Names

- [x] 4.1 Update `NAMES[(UID_ELECTRICITY_SPOT_AVERAGE_PRICE, LANG_EN)]` to `"Monthly average price (EPEX SPOT)"`
- [x] 4.2 Update `NAMES[(UID_ELECTRICITY_SPOT_AVERAGE_PRICE, LANG_NL)]` to `"Gemiddelde maandprijs (EPEX SPOT)"`

## 5. sensor.py — ElectricitySpotAverageSensor

- [x] 5.1 Change `_on_update` to read `store.monthly_average` instead of `store.average`
- [x] 5.2 Add `history` to `extra_state_attributes`: `{d.isoformat(): v for d, v in store._daily_avg_buffer.items()}` (empty dict if store unavailable)

## 6. sensor.py — ElectricitySpotCurrentPriceSensor

- [x] 6.1 Remove `average` key from `extra_state_attributes` in `ElectricitySpotCurrentPriceSensor`

## 7. Validate

- [x] 7.1 Verify `sensor.electricity_spot_average_price` state reflects monthly average after HA restart (buffer loaded from storage)
- [x] 7.2 Verify `history` attribute contains expected ISO-date keys
- [x] 7.3 Verify `sensor.electricity_spot_current_price` attributes no longer contain `average`
- [x] 7.4 Verify display names are correct in both `en` and `nl`
