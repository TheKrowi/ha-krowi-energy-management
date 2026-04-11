## Context

`NordpoolBeStore` currently fetches one day at a time (today + optionally tomorrow) from the public Nord Pool dataportal API (`https://dataportal-api.nordpoolgroup.com/api/DayAheadPrices?date=YYYY-MM-DD`). The store computes `average` as the mean of today's 96 × 15-min slots only.

`sensor.electricity_spot_average_price` exposes that daily average. The export price formula references this sensor, but Belgian dynamic-contract suppliers settle export compensation against a calendar-month average — making the daily average a poor approximation, especially early in the day when few slots have been seen.

Gas (`TtfDamStore`) already fetches a rolling calendar-month window in a single API call. Electricity cannot do this because the Nord Pool API is single-date only. The solution is to accumulate daily averages over time.

## Goals / Non-Goals

**Goals:**
- `sensor.electricity_spot_average_price` reports a rolling calendar-month average matching the `today - relativedelta(months=1)` window used by gas.
- The buffer survives HA restarts via HA's built-in `homeassistant.helpers.storage.Store`.
- On a fresh install, the buffer self-fills via sequential backfill calls (≤29) at startup — no user action needed.
- On restart after N days offline, only N-1 gap-fill calls are made.
- Midnight snapshot captures yesterday's completed average for free (zero extra API calls in steady state).
- A `history` attribute on `sensor.electricity_spot_average_price` exposes the per-day buffer for future visualisation.

**Non-Goals:**
- No authenticated Nord Pool Market Data API — the public unauthenticated dataportal endpoint is sufficient.
- No separate sensor for the daily average — it is dropped in favour of the monthly average.
- No changes to gas, number entities, import price, or export price formula logic.

## Decisions

### D1 — Buffer lives inside `NordpoolBeStore` (not a separate class)

The midnight snapshot reads `self.average` (mean of today's completed slots) before overwriting `_data_today`. Inlining this in the store avoids inter-object coordination. The store is already the single source of truth for Nord Pool data.

*Alternative considered: separate `NordpoolHistoryStore`* — rejected because it would require the main store to call the history store at midnight, adding coupling with no architectural benefit.

### D2 — Buffer key is `date`, value is daily average `float`

```python
_daily_avg_buffer: dict[date, float]
# e.g. {date(2026,3,12): 8.45123, ..., date(2026,4,10): 9.87600}
# today is never in the dict — it's live from self.average
```

Keys are `datetime.date` objects in memory, ISO-string keys (`"YYYY-MM-DD"`) in JSON storage. Buffer excludes today; today's live average is always appended at compute time.

### D3 — Trim window: `today - relativedelta(months=1)`

Uses `dateutil.relativedelta` (already a dependency via gas) for self-adjusting calendar-month arithmetic. Any buffer entry with `date < today - relativedelta(months=1)` is dropped on every trim.

*Alternative: `timedelta(days=30)`* — rejected to match gas exactly and handle short months correctly.

### D4 — Backfill on startup: sequential, ~1 s apart

On startup, the store computes the required date range `(today - relativedelta(months=1))` to `yesterday`. Any date in that range missing from the loaded buffer is fetched sequentially via `_async_fetch(date_str)`. The Nord Pool burst limit is 100 requests / 10 s; 29 calls easily fits. Each call reuses the existing `_async_fetch` method.

If a backfill call fails, that date is silently skipped (buffer stays partial). No retry loop — the gap will persist until the next day when the midnight snapshot fills it naturally for the following days. This is acceptable since a partial buffer gives a slightly less accurate average rather than a complete failure.

### D5 — Persistence via `homeassistant.helpers.storage.Store`

Storage key: `"krowi_energy_management_nordpool_daily_avg"`. The store is loaded once at `async_start` and saved after every write (midnight snapshot + backfill). Format:

```json
{"version": 1, "data": {"2026-03-12": 8.45123, ...}}
```

*Alternative: HA entity attributes (restore via `RestoreEntity`)* — rejected because `RestoreEntity` is for `NumberEntity` / `SensorEntity` subclasses, not store-layer objects. `Storage.Store` is the correct HA primitive for component-level persistent data.

### D6 — `monthly_average` property replaces `average` for sensor use

```python
@property
def monthly_average(self) -> float | None:
    today_avg = self.average  # live mean of today's slots so far
    if today_avg is None:
        return None
    completed = list(self._daily_avg_buffer.values())
    if not completed:
        return round(today_avg, 5)
    return round(mean([*completed, today_avg]), 5)
```

`self.average` (daily mean of `_data_today`) is retained unchanged — it's still internally useful for the midnight snapshot and `low_price` / `price_percent_to_average` attributes.

### D7 — Midnight ordering

```
_on_midnight():
  ① _snapshot_today()     # reads self.average before _data_today is replaced
  ② async_fetch_today()   # overwrites _data_today with new day
```

Order is critical: snapshot must fire before the fetch so yesterday's average is captured from the still-valid `_data_today`.

## Risks / Trade-offs

**[Risk] First-install latency (~30 s backfill)** → Acceptable one-time cost. Store dispatches `SIGNAL_NORDPOOL_UPDATE` after backfill completes so sensors can update. During backfill, `monthly_average` is partially populated (day 1: only today's average).

**[Risk] Backfill call fails for a date** → That date is skipped silently; buffer is partial. Mitigation: the gap compounds slowly — each subsequent midnight fills the next day, so the buffer becomes complete within 30 days regardless.

**[Risk] HA Storage file corruption** → `Store.async_load()` returns `None` on failure; code defaults to empty buffer and triggers full backfill, identical to fresh install.

**[Risk] Clock/timezone edge case at midnight** → `date.today()` used for buffer keys; `dt_utils.now()` used for slot matching. Midnight snapshot uses `date.today() - timedelta(days=1)` which is evaluated after the midnight tick fires — correct.

## Migration Plan

No data migration needed. On first deployment of this change:
1. Store loads (buffer file absent → empty dict).
2. Backfill runs at startup → buffer populated.
3. `sensor.electricity_spot_average_price` state transitions from daily-average to monthly-average immediately after backfill.
4. `average` attribute removed from `sensor.electricity_spot_current_price` — any HA automations using `state_attr('sensor.electricity_spot_current_price', 'average')` will break. Low risk (internal/undocumented attribute).

No rollback strategy needed — reverting the code restores the prior behaviour; buffer storage file is harmlessly ignored.
