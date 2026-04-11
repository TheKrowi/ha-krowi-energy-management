## MODIFIED Requirements

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

### Requirement: Store exposes derived attributes
The store SHALL expose the following computed properties:

| Property | Type | Description |
|---|---|---|
| `current_price` | `float \| None` | Value of the currently active 15-min slot |
| `average` | `float \| None` | Mean of all `value` entries in `data_today` (using `statistics.mean`), rounded to 5 dp |
| `monthly_average` | `float \| None` | `mean([*_daily_avg_buffer.values(), average])` rounded to 5 dp; `None` if `average` is `None` |
| `low_price` | `bool \| None` | `True` if `current_price < average * low_price_cutoff`; `None` if either is `None` |
| `price_percent_to_average` | `float \| None` | `current_price / average` rounded to 5 decimal places; `None` if either is `None` |
| `today` | `list[float]` | All 96 `value` entries in chronological order |
| `tomorrow` | `list[float]` | All 96 `value` entries for tomorrow, or `[]` if not yet available |
| `tomorrow_valid` | `bool` | `True` if `data_tomorrow` contains a full 96-slot dataset |

#### Scenario: Average computed from 96 slots
- **WHEN** `data_today` contains 96 slots with values
- **THEN** `store.average` SHALL equal `statistics.mean(slot["value"] for slot in data_today)` rounded to 5 decimal places

#### Scenario: Monthly average with full buffer
- **WHEN** `_daily_avg_buffer` has 30 entries and `self.average = 9.50000`
- **THEN** `store.monthly_average` SHALL equal `round(mean([*buffer_values, 9.50000]), 5)`

#### Scenario: Monthly average when store has no data
- **WHEN** `self.average` is `None`
- **THEN** `store.monthly_average` SHALL be `None`

#### Scenario: Low price flag when price is below cutoff
- **WHEN** `current_price = 7.5`, `average = 10.0`, `low_price_cutoff = 1.0`
- **THEN** `store.low_price` SHALL be `True`

#### Scenario: Low price flag when price is above cutoff
- **WHEN** `current_price = 12.0`, `average = 10.0`, `low_price_cutoff = 1.0`
- **THEN** `store.low_price` SHALL be `False`
