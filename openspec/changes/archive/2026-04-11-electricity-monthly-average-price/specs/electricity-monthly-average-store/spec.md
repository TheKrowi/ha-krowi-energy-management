## ADDED Requirements

### Requirement: Store maintains a rolling calendar-month daily average buffer
`NordpoolBeStore` SHALL maintain a `_daily_avg_buffer: dict[date, float]` mapping each completed calendar day to its mean spot price in `c€/kWh`. The buffer window SHALL cover `today - relativedelta(months=1)` (exclusive) to `yesterday` (inclusive), matching the gas window exactly. Today's average is never stored in the buffer; it is always computed live from `_data_today`.

#### Scenario: Buffer contains completed days only
- **WHEN** today is `2026-04-11`
- **THEN** `_daily_avg_buffer` SHALL contain entries for dates in `[2026-03-11, ..., 2026-04-10]`
- **THEN** `2026-04-11` SHALL NOT be a key in `_daily_avg_buffer`

#### Scenario: Buffer window adjusts for short months
- **WHEN** today is `2026-03-01`
- **THEN** the oldest retained entry SHALL be `2026-02-01` (self-adjusting via `relativedelta`)

---

### Requirement: Store persists the buffer across restarts via HA Storage
The store SHALL use `homeassistant.helpers.storage.Store` with key `"krowi_energy_management_nordpool_daily_avg"` and version `1` to persist `_daily_avg_buffer`. The buffer SHALL be loaded at `async_start` before any fetches or backfill. The buffer SHALL be saved after every write (backfill and midnight snapshot). JSON keys SHALL be ISO date strings (`"YYYY-MM-DD"`); values SHALL be floats.

#### Scenario: Buffer survives HA restart
- **WHEN** HA restarts with a populated storage file
- **THEN** `_daily_avg_buffer` SHALL be restored from storage on `async_start`
- **THEN** no backfill calls SHALL be made for dates already present in the buffer

#### Scenario: Missing or corrupt storage file
- **WHEN** the storage file is absent or `Store.async_load()` returns `None`
- **THEN** `_daily_avg_buffer` SHALL be initialised as an empty `dict`
- **THEN** startup backfill SHALL run as on a fresh install

---

### Requirement: Store backfills missing days at startup
On `async_start`, after loading the buffer from storage, the store SHALL compute the set of dates in the window `[today - relativedelta(months=1), yesterday]` that are absent from the buffer. For each missing date in sorted ascending order the store SHALL call `_async_fetch(date_str)`, compute the daily average from the returned slots, and insert the result into the buffer. Backfill SHALL run sequentially. If a fetch for a date fails, that date SHALL be silently skipped.

#### Scenario: Fresh install backfill
- **WHEN** the buffer is empty on first install and today is `2026-04-11`
- **THEN** the store SHALL fetch dates `2026-03-11` through `2026-04-10` (up to 30 calls)
- **THEN** each successfully fetched date SHALL be inserted into `_daily_avg_buffer`
- **THEN** `SIGNAL_NORDPOOL_UPDATE` SHALL be dispatched once after all backfill completes

#### Scenario: Partial backfill after N days offline
- **WHEN** HA was offline for 3 days and the buffer is missing `2026-04-08` and `2026-04-09`
- **THEN** only those 2 dates SHALL be fetched
- **THEN** existing buffer entries SHALL be unchanged

#### Scenario: Backfill fetch failure is silently skipped
- **WHEN** the API returns an error for one date during backfill
- **THEN** that date SHALL not be added to `_daily_avg_buffer`
- **THEN** other backfill dates SHALL still be fetched and stored

---

### Requirement: Store snapshots yesterday's average at midnight
At midnight (existing `_on_midnight` handler), the store SHALL call `_snapshot_today()` BEFORE calling `async_fetch_today()`. `_snapshot_today()` SHALL read `self.average` (the live mean of the day that just ended from `_data_today`), store it as `_daily_avg_buffer[yesterday]`, trim the buffer, and persist to storage. If `self.average` is `None`, the snapshot SHALL be skipped.

#### Scenario: Midnight snapshot captures yesterday's average
- **WHEN** midnight fires and `self.average = 9.87600`
- **THEN** `_daily_avg_buffer[date.today() - timedelta(days=1)]` SHALL be `9.87600`
- **THEN** the buffer SHALL be saved to storage
- **THEN** `async_fetch_today()` SHALL be called after the snapshot

#### Scenario: Midnight snapshot skipped if no data
- **WHEN** midnight fires and `self.average` is `None` (API was unavailable all day)
- **THEN** no entry SHALL be added to `_daily_avg_buffer` for yesterday

---

### Requirement: Store trims the buffer to the calendar-month window on every write
After every buffer write (backfill insert or midnight snapshot), the store SHALL remove all entries where `date < today - relativedelta(months=1)`.

#### Scenario: Old entries are removed after trim
- **WHEN** today is `2026-04-11` and the buffer contains an entry for `2026-03-10`
- **THEN** after trim, `2026-03-10` SHALL NOT be in `_daily_avg_buffer`

---

### Requirement: Store exposes a monthly_average property
`NordpoolBeStore` SHALL expose a `monthly_average` property that returns `round(mean([*_daily_avg_buffer.values(), self.average]), 5)`. If `self.average` is `None` the property SHALL return `None`. If the buffer is empty but `self.average` is not `None`, the property SHALL return `round(self.average, 5)`.

#### Scenario: Monthly average with full buffer
- **WHEN** `_daily_avg_buffer` contains 30 values and `self.average = 9.50000`
- **THEN** `monthly_average` SHALL equal `round(mean([*buffer_values, 9.50000]), 5)`

#### Scenario: Monthly average on day 1 (empty buffer)
- **WHEN** `_daily_avg_buffer` is empty and `self.average = 9.50000`
- **THEN** `monthly_average` SHALL be `9.50000`

#### Scenario: Monthly average when store has no data
- **WHEN** `self.average` is `None`
- **THEN** `monthly_average` SHALL be `None`
