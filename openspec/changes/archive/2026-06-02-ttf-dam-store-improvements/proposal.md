## Why

`TtfDamStore` currently holds no persistent state. After a HA restart with the Elindus API temporarily unreachable, both gas spot sensors (`gas_spot_today_price`, `gas_spot_average_price`) are `unavailable` until the next successful fetch — potentially 30+ minutes.

Additionally, the rolling average (`store.average`) is sourced directly from the opaque `statistics.averagePrice` field returned by the Elindus API. Live API analysis confirmed this field is simply the arithmetic mean of all entries in the requested query window (confirmed to be a rolling ~32-day window due to an API off-by-one on the `from` date). This rolling window straddles two billing months mid-month and does not match the calendar-month average that Belgian gas suppliers use for settlement.

Three further correctness bugs exist in the current store:

1. **Timezone bug** — `date.today()` uses system/UTC time. On Docker HA (UTC default), at Brussels midnight the freshness check (`last_date == date.today()`) incorrectly marks yesterday's data as fresh for today, stopping the retry loop prematurely. The same bug affects the Unix ms timestamp→date conversion for the last data point.
2. **Midnight race condition** — `_on_midnight` (hour=0, minute=0, second=1) and `_on_tick` (minute=[0,30], second=1) both fire at exactly 00:00:01, spawning two concurrent fetch tasks.
3. **No month-to-date average** — users have no sensor representing the calendar-month average TTF DAM price, which is the figure suppliers use for billing.

## What Changes

- **MODIFIED** `TtfDamStore` — adds a `_daily_buffer: dict[date, float]` persisted to HA Storage (key `"krowi_energy_management_ttf_dam_daily"`). On fetch, all entries returned by the API are merged into the buffer (not just the last one). The buffer is trimmed to a rolling 1-month window and saved after each merge. `rolling_average` and `month_average` are computed locally from the buffer. `statistics.averagePrice` from the API response is ignored. Adds `_fetch_in_flight: bool` guard to prevent concurrent fetches. Replaces all `date.today()` calls with `dt_utils.now().date()` and uses `dt_utils.as_local()` when converting Unix ms timestamps to local date.
- **NEW** `gas_spot_month_average_price` sensor — calendar-month-to-date average TTF DAM price in `c€/kWh`. Sourced from the new `store.month_average` property. Subscribes to `SIGNAL_TTF_DAM_UPDATE`.
- **MODIFIED** `gas_spot_average_price` sensor — semantics updated: now reports the locally-computed rolling ~30-day average from the buffer instead of the API's opaque `statistics.averagePrice`. Value may differ slightly from the old value due to the off-by-one correction.

## Capabilities

### Modified Capabilities

- `ttf-dam-store`: Buffer-based persistence, locally-computed rolling average and month-to-date average, timezone fix, race fix.
- `gas-spot-sensors`: Adds `gas_spot_month_average_price` sensor; updates `gas_spot_average_price` semantics to locally-computed rolling average.

## Impact

- **Modified**: `custom_components/krowi_energy_management/ttf_dam_store.py` — core store rewrite
- **Modified**: `custom_components/krowi_energy_management/sensor_gas.py` — new sensor class, updated average sensor
- **Modified**: `custom_components/krowi_energy_management/const.py` — new UID and display names
- **Modified**: `custom_components/krowi_energy_management/strings.json`, `translations/en.json`, `translations/nl.json` — new sensor strings
- **Modified**: `tests/test_ttf_dam_store.py` — updated + new tests
