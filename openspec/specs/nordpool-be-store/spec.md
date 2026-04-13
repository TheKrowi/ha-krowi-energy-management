# Spec: nordpool-be-store

## Purpose

Defines the `NordpoolBeStore` — an in-memory cache of Nord Pool BE day-ahead 15-minute price slots, lifecycle management, scheduled fetches, and the signal that drives spot sensor updates.

## Requirements

### Requirement: Nord Pool BE store fetches and caches day-ahead prices
The component SHALL maintain a `NordpoolBeStore` instance in `hass.data[DOMAIN]["nordpool_store"]` for the lifetime of the integration. The store SHALL fetch 15-minute day-ahead price slots for region `BE` in `EUR` from `https://dataportal-api.nordpoolgroup.com/api/DayAheadPrices` and cache them in memory.

The store SHALL parse each entry in `multiAreaEntries` into a slot of the form `{"start": datetime, "end": datetime, "value": float}` where `value = entryPerArea["BE"] / 10` (converting `EUR/MWh` to `c€/kWh`). Timestamps SHALL be parsed with `datetime.fromisoformat()` and SHALL remain timezone-aware.

#### Scenario: Store is initialised on component setup
- **WHEN** the `krowi_energy_management` integration loads
- **THEN** a `NordpoolBeStore` instance SHALL be created and stored in `hass.data[DOMAIN]["nordpool_store"]`
- **THEN** `async_fetch_today()` SHALL be called immediately
- **THEN** if the current time is at or after 13:00 CET, `async_fetch_tomorrow()` SHALL also be called

#### Scenario: API response is parsed into slots
- **WHEN** the API returns an entry `{"deliveryStart": "2026-04-10T00:00:00Z", "deliveryEnd": "2026-04-10T00:15:00Z", "entryPerArea": {"BE": 76.92}}`
- **THEN** the store SHALL contain a slot `{"start": datetime(2026, 4, 10, 0, 0, tzinfo=UTC), "end": datetime(2026, 4, 10, 0, 15, tzinfo=UTC), "value": 7.692}`

#### Scenario: Store cleaned up on integration unload
- **WHEN** the integration is unloaded
- **THEN** all time-change subscriptions registered by the store SHALL be cancelled
- **THEN** `hass.data[DOMAIN]["nordpool_store"]` SHALL be removed

---

### Requirement: Store fetches today's prices once per day at midnight
The store SHALL subscribe to `async_track_time_change(hour=0, minute=0, second=1)`. When this fires, the store SHALL:
1. Call `_snapshot_today()` to capture yesterday's completed average into `_daily_avg_buffer` BEFORE clearing `_data_today`.
2. Call `async_fetch_today()` to refresh today's price cache and clear the tomorrow cache.

#### Scenario: Midnight refresh with snapshot
- **WHEN** the clock reaches 00:00:01 and `self.average` is not `None`
- **THEN** the store SHALL snapshot `self.average` into `_daily_avg_buffer` for yesterday
- **THEN** the store SHALL fetch a fresh set of today's prices from the API
- **THEN** the store's `data_tomorrow` SHALL be reset and `tomorrow_valid` set to `False`

#### Scenario: Midnight refresh ordering
- **WHEN** the clock reaches 00:00:01
- **THEN** `_snapshot_today()` SHALL complete before `async_fetch_today()` is called

---

### Requirement: Store fetches tomorrow's prices after 13:00 CET
The store SHALL subscribe to `async_track_time_change(hour=13, minute=1, second=0)`. When this fires and `tomorrow_valid` is `False`, the store SHALL call `async_fetch_tomorrow()`. If the fetch returns no data (prices not yet published), the store SHALL retry on the next 15-minute tick until data is available.

#### Scenario: Tomorrow prices fetched after publication
- **WHEN** the clock reaches 13:01:00 and tomorrow's prices have been published on the Nord Pool API
- **THEN** the store SHALL populate `data_tomorrow` with 96 price slots for the next calendar day
- **THEN** `tomorrow_valid` SHALL be set to `True`

#### Scenario: Tomorrow prices not yet available at 13:01
- **WHEN** the clock reaches 13:01:00 but the API returns no data for tomorrow
- **THEN** `tomorrow_valid` SHALL remain `False`
- **THEN** `async_fetch_tomorrow()` SHALL be retried on the next 15-min tick

---

### Requirement: Store dispatches a signal on every 15-minute tick
The store SHALL subscribe to `async_track_time_change(minute=[0, 15, 30, 45], second=1)`. On each tick it SHALL update `current_price` from the cached `data_today` array and dispatch `SIGNAL_NORDPOOL_UPDATE` via `async_dispatcher_send`.

#### Scenario: Tick updates current price from cache
- **WHEN** the clock reaches any quarter-hour mark + 1 second
- **THEN** the store SHALL find the slot in `data_today` where `slot["start"] <= now() < slot["end"]`
- **THEN** `store.current_price` SHALL be set to that slot's `value`
- **THEN** `SIGNAL_NORDPOOL_UPDATE` SHALL be dispatched
- **THEN** no API call SHALL be made

#### Scenario: No matching slot found
- **WHEN** `data_today` is empty or `None`
- **THEN** `store.current_price` SHALL be `None`
- **THEN** `SIGNAL_NORDPOOL_UPDATE` SHALL still be dispatched

---

### Requirement: Store exposes derived attributes
The store SHALL expose the following computed properties:

| Property | Type | Description |
|---|---|---|
| `current_price` | `float \| None` | Value of the currently active 15-min slot |
| `average` | `float \| None` | Mean of all `value` entries in `data_today` (using `statistics.mean`), rounded to 5 dp |
| `monthly_average` | `float \| None` | `mean([*_daily_avg_buffer.values(), average])` rounded to 5 dp; `None` if `average` is `None` |
| `monthly_average_rlp` | `float \| None` | RLP-weighted mean of all 15-min slots in the rolling calendar-month window; `None` if today's `average` is `None`. Falls back to unweighted when RLP weights unavailable for a day (see requirement below) |
| `low_price` | `bool \| None` | `True` if `current_price < average * low_price_cutoff`; `None` if either is `None` |
| `price_percent_to_average` | `float \| None` | `current_price / average` rounded to 5 decimal places; `None` if either is `None` |
| `today` | `list[float]` | All 96 `value` entries in chronological order |
| `tomorrow` | `list[float]` | All 96 `value` entries for tomorrow, or `[]` if not yet available |
| `tomorrow_valid` | `bool` | `True` if `data_tomorrow` contains a full 96-slot dataset |

#### Scenario: Average computed from 96 slots
- **WHEN** `data_today` contains 96 slots with values
- **THEN** `store.average` SHALL equal `statistics.mean(slot["value"] for slot in data_today)` rounded to 5 decimal places

#### Scenario: RLP-weighted monthly average with full buffer
- **WHEN** `_daily_rlp_buffer` has 30 entries (each a `(weighted_sum, weight_sum)` tuple) and today's RLP-weighted contribution is available
- **THEN** `store.monthly_average_rlp` SHALL equal `round(sum(ws) / sum(wt), 5)` where `ws` and `wt` are collected from all buffer entries plus today's live contribution

#### Scenario: RLP monthly average with unweighted fallback day
- **WHEN** `SynergridRLPStore` does not have weights for one day in the window
- **THEN** that day's contribution SHALL use `weight_sum = len(slots)` and `weighted_sum = sum(slot["value"] for slot in slots)` (equivalent to unweighted mean)

#### Scenario: Monthly average with full buffer
- **WHEN** `_daily_avg_buffer` has 30 entries and `self.average = 9.50000`
- **THEN** `store.monthly_average` SHALL equal `round(mean([*buffer_values, 9.50000]), 5)`

#### Scenario: Monthly average when store has no data
- **WHEN** `self.average` is `None`
- **THEN** `store.monthly_average` SHALL be `None`
- **THEN** `store.monthly_average_rlp` SHALL be `None`

#### Scenario: Low price flag when price is below cutoff
- **WHEN** `current_price = 7.5`, `average = 10.0`, `low_price_cutoff = 1.0`
- **THEN** `store.low_price` SHALL be `True`

#### Scenario: Low price flag when price is above cutoff
- **WHEN** `current_price = 12.0`, `average = 10.0`, `low_price_cutoff = 1.0`
- **THEN** `store.low_price` SHALL be `False`

---

### Requirement: Store maintains a second RLP-weighted monthly average

The `NordpoolBeStore` SHALL maintain a **second** daily buffer `_daily_rlp_buffer:
dict[date, tuple[float, float]]` alongside the existing unweighted `_daily_avg_buffer:
dict[date, float]`. The two buffers are independent; the existing buffer and
`monthly_average` property are **unchanged**.

The store SHALL accept a `SynergridRLPStore` reference in `async_start()` for use only
by the RLP buffer.

**RLP buffer format:** `dict[date, tuple[float, float]]`
- `weighted_sum` = `sum(slot["value"] × rlp_weight[i] for i, slot in enumerate(slots))`
- `weight_sum` = `sum(rlp_weight[i] for i in range(len(slots)))`
- Fallback when RLP weights unavailable: `weighted_sum = sum(values)`, `weight_sum = len(slots)`

**`monthly_average_rlp` formula:**
```
monthly_average_rlp = sum(ws for (ws, wt) in all_days) / sum(wt for (ws, wt) in all_days)
```
where `all_days` = `_daily_rlp_buffer.values()` + today's live RLP contribution.

The RLP buffer SHALL be persisted in HA Storage under a separate key:
`krowi_energy_management_nordpool_daily_rlp_avg`.

#### Scenario: Midnight snapshot writes to both buffers
- **WHEN** the clock reaches 00:00:01
- **THEN** `_snapshot_today()` SHALL write the unweighted average to `_daily_avg_buffer` (unchanged)
- **THEN** `_snapshot_today()` SHALL also write `(weighted_sum, weight_sum)` to `_daily_rlp_buffer`
- **THEN** if RLP weights are unavailable for yesterday, the RLP entry SHALL use the unweighted fallback

#### Scenario: monthly_average unchanged
- **WHEN** `_daily_avg_buffer` has 30 float entries and `self.average = 9.50000`
- **THEN** `store.monthly_average` SHALL equal `round(mean([*buffer_values, 9.50000]), 5)` (unweighted, identical to pre-RLP behaviour)

---

### Requirement: Store handles API errors gracefully
If the API call fails (HTTP error, timeout, or unexpected response shape), the store SHALL log an error, leave the existing cache unchanged (or empty if first load), and set `current_price` to `None`. Sensors SHALL become `unavailable` when `current_price` is `None`.

#### Scenario: API returns HTTP error
- **WHEN** the Nord Pool API returns a non-2xx response
- **THEN** the store SHALL log an error at the `ERROR` level
- **THEN** the existing `data_today` cache SHALL be unchanged
- **THEN** `SIGNAL_NORDPOOL_UPDATE` SHALL be dispatched so sensors update to `unavailable`

#### Scenario: API response missing expected fields
- **WHEN** the response JSON does not contain `multiAreaEntries` or `entryPerArea.BE`
- **THEN** the store SHALL log an error and treat the fetch as failed
