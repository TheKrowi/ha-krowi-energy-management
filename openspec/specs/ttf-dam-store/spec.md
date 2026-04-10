# Spec: ttf-dam-store

## Purpose

Defines the `TtfDamStore` — the internal store that fetches, caches, and serves daily TTF DAM gas prices for the `krowi_energy_management` integration. The store is owned by the gas config entry and lives for its lifetime.

## Requirements

### Requirement: TTF DAM store fetches and caches daily gas prices
The component SHALL maintain a `TtfDamStore` instance in `hass.data[DOMAIN]["ttf_dam_store"]` for the lifetime of the gas config entry. The store SHALL fetch daily TTF DAM prices from `https://mijn.elindus.be/marketinfo/dayahead/prices` with `market=GAS&granularity=DAY` and cache the results in memory. Query parameters: `from = (today - relativedelta(months=1)).isoformat()`, `to = today.isoformat()`.

The store SHALL read `response["statistics"]["averagePrice"]` and divide by `10` to obtain the rolling calendar-month `average` in `c€/kWh`. It SHALL sort `response["dataSeries"]["data"]` by `x` (ascending) and take the last entry's `y` divided by `10` as `today_price` in `c€/kWh`.

#### Scenario: Store is initialised on gas entry setup
- **WHEN** the gas config entry is loaded
- **THEN** a `TtfDamStore` SHALL be created and stored in `hass.data[DOMAIN]["ttf_dam_store"]`
- **THEN** `async_fetch()` SHALL be called immediately

#### Scenario: API response is parsed into store properties
- **WHEN** the API returns `statistics.averagePrice = 52.90` and the last `dataSeries.data` entry has `y = 45.43`
- **THEN** `store.average` SHALL be `5.29` (c€/kWh, i.e. `52.90 / 10`)
- **THEN** `store.today_price` SHALL be `4.543` (c€/kWh, i.e. `45.43 / 10`)

#### Scenario: Fetch window spans one calendar month on a 31-day month
- **WHEN** today is March 15
- **THEN** `from` SHALL be `"2026-02-15"` (one calendar month prior)
- **THEN** `to` SHALL be `"2026-03-15"`

#### Scenario: Fetch window clamps correctly for end-of-month dates
- **WHEN** today is March 31
- **THEN** `from` SHALL be `"2026-02-28"` (clamped, not February 31)
- **THEN** `to` SHALL be `"2026-03-31"`

#### Scenario: Fetch window spans 28 days in February
- **WHEN** today is February 28 (non-leap year)
- **THEN** `from` SHALL be `"2026-01-28"`
- **THEN** `to` SHALL be `"2026-02-28"`

#### Scenario: Store cleaned up on gas entry unload
- **WHEN** the gas config entry is unloaded
- **THEN** all time-change subscriptions registered by the store SHALL be cancelled
- **THEN** `hass.data[DOMAIN]["ttf_dam_store"]` SHALL be removed

---

### Requirement: Store determines freshness of today's data
After each fetch the store SHALL compare the date of the last entry in `dataSeries.data` (derived by parsing `last["x"]` as a Unix millisecond timestamp) to `date.today()`. If they match, `data_is_fresh` SHALL be set to `True`. Otherwise `data_is_fresh` SHALL be `False`.

#### Scenario: Last data point is dated today
- **WHEN** the latest entry in `dataSeries.data` has `x` corresponding to today's date
- **THEN** `store.data_is_fresh` SHALL be `True`

#### Scenario: Last data point is from a prior day
- **WHEN** the latest entry in `dataSeries.data` has `x` corresponding to yesterday's date (today's data not yet published)
- **THEN** `store.data_is_fresh` SHALL be `False`

---

### Requirement: Store fetches fresh data once per day at midnight
The store SHALL subscribe to `async_track_time_change(hour=0, minute=0, second=1)`. When this fires, the store SHALL set `_data_is_fresh = False` and immediately call `async_fetch()`.

#### Scenario: Midnight refresh
- **WHEN** the clock reaches 00:00:01
- **THEN** `_data_is_fresh` SHALL be reset to `False`
- **THEN** `async_fetch()` SHALL be called
- **THEN** `SIGNAL_TTF_DAM_UPDATE` SHALL be dispatched

---

### Requirement: Store retries on 30-minute ticks until data is fresh
The store SHALL subscribe to `async_track_time_change(minute=[0, 30], second=1)`. On each tick, if `_data_is_fresh` is `False`, the store SHALL call `async_fetch()`. If `_data_is_fresh` is `True`, the tick is a no-op.

#### Scenario: Today's data not yet available at midnight — retry succeeds at 00:30
- **WHEN** the midnight fetch leaves `data_is_fresh = False` (today's point not yet in response)
- **AND** the 00:30:01 tick fires and the API now returns a point dated today
- **THEN** `store.data_is_fresh` SHALL be `True`
- **THEN** `SIGNAL_TTF_DAM_UPDATE` SHALL be dispatched

#### Scenario: Data already fresh — 30-min tick is a no-op
- **WHEN** `data_is_fresh` is `True`
- **AND** the next 30-min tick fires
- **THEN** no API call SHALL be made

---

### Requirement: Store dispatches a signal after every fetch attempt
The store SHALL dispatch `SIGNAL_TTF_DAM_UPDATE` via `async_dispatcher_send` after every call to `async_fetch()`, whether the fetch succeeded, failed, or the data remained stale.

#### Scenario: Signal dispatched on successful fresh fetch
- **WHEN** `async_fetch()` succeeds and `data_is_fresh` becomes `True`
- **THEN** `SIGNAL_TTF_DAM_UPDATE` SHALL be dispatched so sensors update

#### Scenario: Signal dispatched even when API fails
- **WHEN** `async_fetch()` encounters an HTTP error or parse error
- **THEN** the store cache SHALL remain unchanged
- **THEN** `SIGNAL_TTF_DAM_UPDATE` SHALL still be dispatched so sensors reflect `unavailable`

---

### Requirement: Store exposes derived properties
The store SHALL expose the following properties:

| Property | Type | Description |
|---|---|---|
| `today_price` | `float \| None` | Latest daily TTF DAM price in `c€/kWh`; `None` until first successful fetch |
| `average` | `float \| None` | 30-day average price in `c€/kWh`; `None` until first successful fetch |
| `data_is_fresh` | `bool` | `True` if the latest fetched data point is dated today |

#### Scenario: Properties are None before first fetch
- **WHEN** the store has been initialised but `async_fetch()` has not yet completed
- **THEN** `store.today_price` and `store.average` SHALL both be `None`
- **THEN** `store.data_is_fresh` SHALL be `False`

---

### Requirement: Store handles API errors gracefully
If the API request fails (HTTP error, timeout, invalid JSON, `KeyError`, `ValueError`), the store SHALL log an error at `ERROR` level, leave all cached properties unchanged, and still dispatch `SIGNAL_TTF_DAM_UPDATE`.

#### Scenario: HTTP 500 from API
- **WHEN** the Elindus API returns an HTTP 500
- **THEN** `store.today_price` and `store.average` SHALL retain their previous values (or `None` if no prior successful fetch)
- **THEN** `SIGNAL_TTF_DAM_UPDATE` SHALL be dispatched
