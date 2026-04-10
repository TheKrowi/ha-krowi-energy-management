## Context

The `embed-nordpool-be-fetcher` change eliminated the electricity domain's dependency on the external Nord Pool HACS component by embedding a `NordpoolBeStore` directly in `krowi_energy_management`. The gas domain still depends on the external `krowi_ttf_dam` component via a configurable `current_price_entity`. This change applies the same pattern to gas using the Elindus TTF DAM API.

Key differences from the Nord Pool store:

- **Daily granularity**: TTF DAM data is one price point per day (`granularity=DAY`), not 96 × 15-min slots. There is no intraday slot lookup — just a single value for today and a 30-day average.
- **No fixed publication window**: Unlike Nord Pool's ~13:00 CET tomorrow publication, TTF DAM today's price may arrive from shortly after midnight to several hours later. The availability time varies.
- **No tomorrow prices**: The store only needs `today_price` and a 30-day `average`. There is no "tomorrow" concept.
- **Intraday signals**: Since there is no intraday price variation, the store dispatches a signal only when fresh data is confirmed or on each retry attempt — not on a fixed 15-min tick.

The Elindus API has been validated as functional and unauthenticated. Relevant payload keys confirmed: `statistics.averagePrice` (float, EUR/MWh), `dataSeries.data` (array of `{x: unix_ms, y: float, name: "DD/MM/YYYY HH:MM"}`). Daily points are sorted ascending by `x`; the last entry is today's price.

## Goals / Non-Goals

**Goals:**
- Own the entire TTF DAM gas price data pipeline inside `krowi_energy_management`
- Expose two new sensor entities for gas spot today price and 30-day average price
- Remove `unit` and `current_price_entity` from the gas config entry
- Hardcode gas unit to `c€/kWh`
- Migrate existing v2 gas config entries to v3 cleanly

**Non-Goals:**
- Supporting gas markets other than TTF DAM (hardcoded)
- Supporting currencies other than EUR (hardcoded)
- Exposing multi-day price history beyond today + 30d average
- Intraday price granularity (TTF DAM is daily)
- Replacing `krowi_ttf_dam` as a standalone integration (it remains available; this change makes it optional)

## Decisions

### Decision: Plain store class, not DataUpdateCoordinator

**Chosen**: A plain `TtfDamStore` class with explicit time-event subscriptions.

**Rationale**: Mirrors `NordpoolBeStore`. The store fetches at most a handful of times per day (startup, midnight reset, 30-min retries until fresh). A `DataUpdateCoordinator` with a fixed interval would either poll too frequently or be too coarse to express the retry-until-fresh pattern. The "stop retrying once `data_is_fresh = True`" logic cannot be expressed as a fixed interval.

**Alternative considered**: `DataUpdateCoordinator` with 6-hour interval (same as the old `krowi_ttf_dam` component) — rejected because it polls when data hasn't changed and cannot express the daily-freshness check.

---

### Decision: Retry strategy — 30-minute tick with `data_is_fresh` flag

**Chosen**: Subscribe to `async_track_time_change(minute=[0, 30], second=1)`. On each tick, if `data_is_fresh` is `False`, call `async_fetch()`. When the latest data point in the response is dated today, set `data_is_fresh = True` and stop retrying until the next midnight reset.

**Rationale**: TTF DAM data is sometimes available within minutes of midnight but can be delayed until early morning. Retrying every 30 minutes balances freshness against API politeness. Once data is confirmed fresh for the day, no further fetches are needed until the next midnight.

**Alternative considered**: Hourly ticks — slightly less responsive to early data availability; 30-min preferred.

**Alternative considered**: `async_call_later` with exponential backoff — more complex, harder to reason about, non-deterministic retry schedule. Rejected.

---

### Decision: `data_is_fresh` determined by comparing date of latest data point to `date.today()`

**Chosen**: After each successful fetch, extract the last entry from `dataSeries.data` (sorted by `x`), parse its Unix ms timestamp to a date, and compare to `date.today()`. If they match, `data_is_fresh = True`.

**Rationale**: The API may return yesterday's most recent price before today's data is published. Comparing the date of the last data point is the only reliable way to confirm today's price is present.

**Alternative considered**: Checking `statistics.averagePrice` changes day-over-day — not reliable; the average shifts slightly each day regardless.

---

### Decision: Midnight resets `data_is_fresh` before fetching

**Chosen**: At 00:00:01, set `data_is_fresh = False` first, then immediately call `async_fetch()`.

**Rationale**: Ensures the retry loop restarts each day even if yesterday's fetch had confirmed its own day as fresh.

---

### Decision: Unit conversion at ingest time (EUR/MWh → c€/kWh)

**Chosen**: Divide both `y` (today's price) and `statistics.averagePrice` by `10` during fetch and store the results in `c€/kWh`.

**Rationale**: Mirrors the `NordpoolBeStore` conversion. The gas domain always operates in `c€/kWh`. Converting at ingest removes all downstream unit logic.

**Alternative considered**: Storing raw `EUR/MWh` and converting in the sensor — rejected; reintroduces unit-detection complexity being removed.

---

### Decision: Store lives on `hass.data[DOMAIN]["ttf_dam_store"]`

**Chosen**: Single store instance under the component's domain key.

**Rationale**: Consistent with `hass.data[DOMAIN]["nordpool_store"]` pattern established by the electricity change.

---

### Decision: Config entry migration v2 → v3

**Chosen**: Set `VERSION = 3`. In `async_migrate_entry`, for gas entries at `version = 2`: remove `unit` and `current_price_entity` from `entry.data`, set `version = 3`. For electricity and settings v2 entries: set `version = 3` only (no data changes needed). No-op for v3+.

**Rationale**: Without migration, existing gas installs would have stale fields in `entry.data`. The migration must be idempotent (fields absent → no error).

---

### Decision: `CONF_CURRENT_PRICE_ENTITY` removed from const.py

**Chosen**: Remove `CONF_CURRENT_PRICE_ENTITY` entirely — gas was its last consumer. Remove gas `CONF_UNIT` as well (electricity already removed its `CONF_UNIT` in v2).

**Rationale**: Dead constants create false impressions that the pattern is still in use. Remove cleanly.
