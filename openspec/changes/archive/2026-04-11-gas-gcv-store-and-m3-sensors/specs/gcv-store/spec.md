## ADDED Requirements

### Requirement: GCV store fetches and caches monthly GCV per GOS zone
The component SHALL maintain a `GcvStore` instance in `hass.data[DOMAIN]["gcv_store"]` for the lifetime of the gas config entry. The store SHALL fetch the Atrias GCV file for the prior calendar month from:

```
https://api.atrias.be/roots/download/SectorData%2F02%20Gross%20Calorific%20Values%2F{YEAR}%2FGCV{YEAR}{MM}.txt?subscription-key=41be1fbab53b4a80ba0d17084a338a55
```

The response is CSV with header `GCVMonth,ARSName,ARSEanGSRN,GCVValue`. The store SHALL locate the row where `ARSName` matches `CONF_GOS_ZONE` (case-sensitive) and parse `GCVValue` (comma as decimal separator) as a float.

#### Scenario: Store is initialised on gas entry setup
- **WHEN** the gas config entry is loaded
- **THEN** a `GcvStore` SHALL be created and stored in `hass.data[DOMAIN]["gcv_store"]`
- **THEN** `async_start()` SHALL be called immediately

#### Scenario: Store targets prior month file
- **WHEN** today is April 11, 2026
- **THEN** the store SHALL fetch `GCV202603.txt` (March = prior month)
- **THEN** it SHALL NOT attempt to fetch `GCV202604.txt`

#### Scenario: GCV parsed correctly from CSV
- **WHEN** the API returns a row `2026-03,GOS FLUVIUS - LEUVEN,...,"11,5323038154"`
- **THEN** `store.gcv` SHALL be `11.5323038154`

#### Scenario: Store cleaned up on gas entry unload
- **WHEN** the gas config entry is unloaded
- **THEN** all time subscriptions registered by the store SHALL be cancelled
- **THEN** `hass.data[DOMAIN]["gcv_store"]` SHALL be removed

---

### Requirement: GCV store persists 12-month rolling history
The store SHALL persist a `{ "YYYY-MM": float }` dict in HA storage under key `krowi_energy_management_gcv_history`. The dict SHALL contain at most 12 entries; oldest entries SHALL be pruned when a 13th is added.

#### Scenario: History persists across HA restart
- **WHEN** HA restarts after GCV values have been fetched
- **THEN** the store SHALL load the existing history from HA storage on `async_start()`
- **THEN** no re-fetch SHALL occur for months already present in history

#### Scenario: History pruned to 12 entries
- **WHEN** a 13th monthly entry is added to history
- **THEN** the oldest entry SHALL be removed so history contains exactly 12 entries

---

### Requirement: GCV store fills missing history on startup
On every `async_start()`, the store SHALL compute the 12 most recent prior-month targets. For each target month not already in `history`, the store SHALL attempt to fetch its GCV file (oldest missing month first). Successful fetches are appended to history and saved. A 404 response for a given month SHALL be silently skipped.

#### Scenario: First install — bootstraps 12 months
- **WHEN** history is empty on first install
- **THEN** the store SHALL attempt to fetch the 12 most recent prior-month GCV files
- **THEN** successfully fetched months SHALL be stored in history

#### Scenario: Partial history — fills only missing months
- **WHEN** history contains 8 entries on restart (e.g. due to prior rate limiting)
- **THEN** only the 4 missing months SHALL be fetched
- **THEN** already-present months SHALL NOT be re-fetched

#### Scenario: Rate limited mid-bootstrap — resumes next restart
- **WHEN** the bootstrap is interrupted (e.g. connection error) after fetching 6 of 12 months
- **THEN** partial history SHALL be saved to HA storage
- **THEN** on next restart, only the remaining missing months SHALL be fetched

---

### Requirement: GCV store marks data_is_fresh and retries daily
After the gap-fill loop, if the most recent prior-month target was successfully fetched, `data_is_fresh` SHALL be `True`. Otherwise `data_is_fresh` SHALL be `False`.

The store SHALL subscribe to `async_track_time_change(hour=6, minute=0, second=1)`. On each tick, if `data_is_fresh` is `False`, the store SHALL retry fetching the current target month. On the 1st of each month the target advances to the new prior month and `data_is_fresh` is reset to `False`.

#### Scenario: File not yet published — retries at 06:00 daily
- **WHEN** today is May 2 and `GCV202604.txt` returns 404
- **THEN** `data_is_fresh` SHALL be `False`
- **THEN** at 06:00:01 on May 3, the store SHALL retry `GCV202604.txt`

#### Scenario: Retry succeeds — marks fresh and dispatches
- **WHEN** `GCV202604.txt` returns 200 at the 06:00:01 retry
- **THEN** `data_is_fresh` SHALL be set to `True`
- **THEN** `SIGNAL_GCV_UPDATE` SHALL be dispatched
- **THEN** no further retry SHALL occur for April's file

#### Scenario: 1st of month resets freshness
- **WHEN** the clock reaches June 1
- **THEN** the store's target SHALL advance to `GCV202605.txt`
- **THEN** `data_is_fresh` SHALL be reset to `False`
- **THEN** `async_fetch()` SHALL be called immediately

---

### Requirement: GCV store dispatches SIGNAL_GCV_UPDATE after each successful fetch
After any successful fetch (bootstrap, normal, or retry), the store SHALL dispatch `SIGNAL_GCV_UPDATE` via `async_dispatcher_send`.

#### Scenario: Signal dispatched after bootstrap completes
- **WHEN** the bootstrap fetch loop completes with at least one successful fetch
- **THEN** `SIGNAL_GCV_UPDATE` SHALL be dispatched once

#### Scenario: Signal dispatched after daily retry succeeds
- **WHEN** a daily 06:00 retry fetch succeeds
- **THEN** `SIGNAL_GCV_UPDATE` SHALL be dispatched
