## Context

`TtfDamStore` is a plain store (not a coordinator) that fetches daily TTF DAM gas prices from the Elindus API (`https://mijn.elindus.be/marketinfo/dayahead/prices`). It is owned by the gas config entry and lives for its lifetime.

The reference pattern for buffer-based persistence is `NordpoolBeStore`, which uses:
- `dict[date, float]` in-memory buffer
- HA `Store` persistence as `{"YYYY-MM-DD": float}`
- Load on startup → trim → save (removes stale entries accumulated during long uptime)
- Merge on each fetch (new API entries overwrite existing keys for same date)
- Fire-and-forget async save after each merge

TTF differs from Nord Pool in one key way: the API already returns the full date-range window in a single call. There is no need for a day-by-day backfill loop — the regular `async_fetch()` merges all returned entries at once, implicitly filling any gaps in the buffer from previous successful fetches.

Live API analysis confirmed:
- `statistics.averagePrice` = arithmetic mean of all entries in the query window — not a calendar-month average, not the Elindus billing figure. Ignored going forward.
- The API returns one extra entry before the `from` date (off-by-one bug). This stray entry is harmlessly merged under its correct date key and falls outside the rolling window trim cutoff.
- The query window `today - relativedelta(months=1) → today` is retained unchanged, ensuring the buffer always covers at least one full rolling month.

## Goals / Non-Goals

**Goals:**
- Persist the daily TTF DAM price series to HA Storage so sensors survive restarts
- Compute rolling ~30d average and calendar-month-to-date average locally from the buffer
- Expose both averages as sensors
- Fix `date.today()` → `dt_utils.now().date()` for correctness on UTC-system Docker HA
- Fix concurrent fetch at midnight via `_fetch_in_flight` guard

**Non-Goals:**
- Changing fetch frequency or the Elindus API endpoint
- Supporting multiple gas markets or currencies
- Exposing raw daily price history to sensors (beyond today + aggregates)
- Backfill retry loop (Nord Pool pattern) — not needed because one API call covers the full window

## Decisions

### Decision: Buffer shape — `dict[date, float]` keyed by local date

**Chosen**: `_daily_buffer: dict[date, float]` stored as `{"YYYY-MM-DD": float}` in HA Storage, key `"krowi_energy_management_ttf_dam_daily"`.

**Rationale**: Mirrors `NordpoolBeStore._daily_avg_buffer`. Identical load/trim/save lifecycle. Date strings serialize cleanly via `isoformat()` / `date.fromisoformat()`.

---

### Decision: Merge all API entries into buffer on each fetch

**Chosen**: On each `async_fetch()` call, iterate all `dataSeries.data` entries, convert Unix ms timestamp to local date via `dt_utils.as_local(datetime.fromtimestamp(x/1000, tz=timezone.utc)).date()`, divide `y` by 10 for c€/kWh, and write `buffer[local_date] = value`. Existing keys are overwritten (idempotent).

**Rationale**: Handles both initial population and incremental daily updates uniformly. The API's off-by-one stray entry (one day before `from`) merges under its correct date and is pruned by `_trim_buffer()` when it falls outside the rolling window.

**Alternative considered**: Only updating `buffer[today]` from the last entry — rejected; wastes the full history the API already returns and leaves the buffer empty on first install until 30 days have elapsed.

---

### Decision: Trim cutoff = `dt_utils.now().date() - relativedelta(months=1)`

**Chosen**: Same cutoff as the API query window. This ensures the buffer never grows beyond ~32 entries.

**Rationale**: Mirrors `NordpoolBeStore._trim_buffer()`. Trim runs on startup (after load) and after each fetch merge.

---

### Decision: Rolling average = mean of all buffer entries within trim cutoff

**Chosen**: `rolling_average = mean(v for d, v in buffer if d >= cutoff)`.

**Rationale**: Produces the same result as the old API `statistics.averagePrice` (corrected for the off-by-one) without trusting an opaque third-party field. Locally computable, verifiable, and consistent across restarts.

---

### Decision: Month-to-date average = mean of buffer entries from 1st of current local month

**Chosen**: `month_average = mean(v for d, v in buffer if d >= today.replace(day=1))`.

**Rationale**: Calendar-month average matches Belgian gas supplier billing convention. On the 1st of the month, only today's entry exists → month_average equals today's price. Noisy early in the month but honest. Follows the same "live data in buffer" pattern.

---

### Decision: `data_is_fresh` derived from buffer

**Chosen**: `data_is_fresh = dt_utils.now().date() in self._daily_buffer`.

**Rationale**: Simpler and more correct than comparing to the last API entry date. After a successful fetch that includes today, the buffer contains today's key → fresh. After midnight reset, today's key is not yet in the buffer → not fresh → retry continues.

**Note**: `_daily_buffer` is NOT cleared at midnight. Only `_data_is_fresh` is reset (same pattern as current store). The buffer persists across midnight ticks; only the `data_is_fresh` flag resets.

---

### Decision: `_fetch_in_flight: bool` guard

**Chosen**: Set `_fetch_in_flight = True` at the start of `async_fetch()`, `False` on exit (in a `finally` block). Both `_on_midnight` and `_on_tick` check `_fetch_in_flight` before spawning a new task.

**Rationale**: Prevents the double-fetch that occurs when both `_on_midnight` and `_on_tick` fire at 00:00:01. No additional locking needed; HA event loop is single-threaded.

---

### Decision: `date.today()` → `dt_utils.now().date()` throughout

**Chosen**: Replace all `date.today()` calls in `TtfDamStore` with `dt_utils.now().date()`.

**Rationale**: `dt_utils.now()` returns the current time in HA's configured timezone (e.g. Europe/Brussels). `date.today()` uses the system/Python clock (UTC on Docker). At Brussels midnight, `date.today()` still returns yesterday's date for 1–2 hours, causing the freshness check to fail incorrectly.

**Scope**: Only `TtfDamStore` is changed in this pass. Other stores (`GcvStore`, `NordpoolBeStore`) have similar issues but are out of scope.

---

### Decision: Unix ms → local date conversion

**Chosen**: `dt_utils.as_local(datetime.fromtimestamp(entry["x"] / 1000, tz=timezone.utc)).date()`.

**Rationale**: The Elindus API timestamps represent midnight in local time but are expressed as UTC Unix ms. Converting via `dt_utils.as_local()` brings them into HA's configured timezone before taking `.date()`, producing the correct local calendar date. Using `.date()` on the UTC datetime would give the wrong date for timestamps near midnight (off by one day for UTC+1/+2).

---

### Decision: `statistics.averagePrice` ignored

**Chosen**: Remove the line that reads `data["statistics"]["averagePrice"]`. Use only `dataSeries.data` entries.

**Rationale**: Confirmed by live API analysis to be the arithmetic mean of the query window — an opaque value we can compute more accurately ourselves. Removing the dependency reduces the blast radius if Elindus changes the response shape.

---

### Decision: New sensor `gas_spot_month_average_price` — separate entity, same signal

**Chosen**: New `GasSpotMonthAveragePriceSensor` class in `sensor_gas.py`. Subscribes to `SIGNAL_TTF_DAM_UPDATE`. Reads `store.month_average`. Unit `c€/kWh`, state class `MEASUREMENT`. UID `gas_spot_month_average_price`.

**Rationale**: Clean separation of concerns. Rolling average retains its existing UID and semantics (with updated computation). Month-to-date is a new concept exposed as a new entity.

**Alternative considered**: Single sensor with a mode option — rejected; adds config complexity, harder to use both values simultaneously in automations/dashboards.
