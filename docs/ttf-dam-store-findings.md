# TtfDamStore — Exploration Findings (2026-06-01)

## What the Elindus averagePrice actually is

Confirmed by live API calls: `statistics.averagePrice` = **simple arithmetic mean of all daily entries
returned in the requested `from`/`to` window**. It is NOT a calendar-month average.

## API off-by-one bug

Despite `from=2026-05-01`, the API returns April 30 as the first entry. The window is always
`len(requested days) + 1` entries. The current fetch (`today - 1 month → today`) therefore
covers ~32 days, not 31.

## Average type: rolling, not calendar-month

The rolling window straddles two billing months mid-month. Belgian gas suppliers settle on the
**calendar-month average** (e.g., May 1–31). The API average does NOT match supplier billing
convention — it is an Elindus-internal figure.

## Planned improvements (to be captured in an openspec change)

1. **Full history persistence** — persist daily series to HA Storage; recompute average locally
   from the stored window (removes trust in opaque `statistics.averagePrice`).
   Decision needed: keep rolling window or switch to calendar-month-to-date (correct for billing).
2. **Midnight race fix** — `_on_midnight` and `_on_tick` both fire at 00:00:01; add
   `_fetch_in_flight: bool` guard.
3. **Timezone fix** — `date.today()` → `dt_utils.now().date()` for freshness check; use
   `dt_utils.as_local()` when converting Unix ms timestamps to local date.

## async_track_time_change timezone behaviour

`async_track_time_change` fires at **HA's configured local timezone** (e.g. Europe/Brussels).
The callbacks themselves are NOT the problem. The bug is inside the callbacks where
`date.today()` uses the Python/system clock (UTC on Docker) instead of HA local time.
