# Spec: synergrid-rlp-store

## Purpose

Defines the `SynergridRLPStore` — a lightweight store that downloads, parses and caches the
annual Synergrid RLP0N electricity profile for Belgium. Provides per-quarter-hour (15-min)
normalized load weights used by `NordpoolBeStore` to compute an RLP-weighted monthly EPEX
average, matching the formula used by Belgian variable-rate suppliers such as Mega.

## Background

Belgian variable-rate suppliers define the monthly EPEX average as:

> "gemiddelde kwartierwaarden Day Ahead EPEX SPOT Belgium tijdens de leveringsmaand,
> **gewogen met het RLP-profiel** (gepubliceerd door Synergrid)"

The RLP0N (Real Load Profile, Normalized) is the ex-ante normalized consumption profile
published annually by Synergrid for all Belgian DSOs. It provides a weight for each
15-minute slot across the entire calendar year that represents the relative share of
residential/small-consumer load in that slot.

Source: https://www.synergrid.be/nl/documentencentrum/statistieken-gegevens/profielen-slp-spp-rlp

## Download URL Pattern

```
https://www.synergrid.be/images/downloads/SLP-RLP-SPP/{YEAR}/RLP0N%20{YEAR}%20Electricity.xlsb
```

Example (2026):
```
https://www.synergrid.be/images/downloads/SLP-RLP-SPP/2026/RLP0N%202026%20Electricity.xlsb
```

The file is a static ex-ante profile published at the start of each calendar year. It
covers all 96 quarter-hours per day for the full year and does not change during the year.

## Dependency

`pyxlsb>=1.0.10` SHALL be added to `manifest.json` `requirements`.
Parsing of the `.xlsb` file SHALL be delegated to `hass.async_add_executor_job` because
`pyxlsb` performs blocking I/O. The file SHALL be downloaded in memory (no disk writes).

## Data Model

Parsed data is stored as `dict[date, list[float]]`:
- Key: calendar date
- Value: list of exactly 96 weight floats (QH1 through QH96, chronological order)
  - On DST spring-forward days the list has 92 entries; on fall-back days, 100 entries.

Weights are stored as-is from the Synergrid file (not normalized to sum to 1).
The weighted average is computed as `sum(price × weight) / sum(weight)`, so absolute
scale does not matter.

## Storage

Parsed weights are persisted in HA Storage under key:
```
krowi_energy_management_rlp_{year}
```
e.g. `krowi_energy_management_rlp_2026` for the 2026 profile.

The store class is `SynergridRLPStore` and lives in `rlp_store.py` alongside `nordpool_store.py`.

## Architecture

A singleton instance is created in `__init__.py` alongside the `NordpoolBeStore` and
stored in `hass.data[DOMAIN]["rlp_store"]`. It is started before the NordpoolBeStore so
that weights are available during the initial buffer load/backfill.

## Requirements

---

### Requirement: RLP store downloads and parses annual profile on startup

On `async_start(hass)`, the store SHALL:

1. Attempt to load persisted data from HA Storage for the current year.
2. Check whether today's date is present in the loaded data.
3. If today's date is **not** covered (first install, year rollover, or corrupt cache):
   download the `.xlsb` file for the current year and parse it.
4. Persist the newly downloaded data to HA Storage.

#### Scenario: First startup, no persisted data
- **WHEN** no HA Storage data exists for the current year
- **THEN** the store SHALL download `RLP0N {YEAR} Electricity.xlsb`
- **THEN** the store SHALL parse and persist 365 (or 366) day entries
- **THEN** `store.has_date(today)` SHALL return `True`

#### Scenario: Startup with valid persisted data
- **WHEN** HA Storage contains valid data for the current year and today's date is present
- **THEN** the store SHALL NOT make any HTTP request
- **THEN** `store.has_date(today)` SHALL return `True`

#### Scenario: Year rollover
- **WHEN** the stored data covers the previous year and today (Jan 1) is not present
- **THEN** the store SHALL download the new year's file
- **THEN** old-year data SHALL be removed from HA Storage (different key, will be left behind
  until HA clears unused storage)

---

### Requirement: RLP store exposes per-day weights

```python
store.get_weights(d: date) -> list[float] | None
store.has_date(d: date) -> bool
```

`get_weights` SHALL return the list of 96 (±4 for DST) weight floats for date `d`, or
`None` if that date is not available (download failed, or date outside the year).

`has_date` SHALL return `True` if and only if weights for `d` are cached.

#### Scenario: Weights available
- **WHEN** `store.has_date(date(2026, 4, 10))` is `True`
- **THEN** `store.get_weights(date(2026, 4, 10))` SHALL return a list of 96 floats

#### Scenario: Weights not available
- **WHEN** RLP data for a date could not be fetched or parsed
- **THEN** `store.get_weights(d)` SHALL return `None`
- **THEN** the caller (NordpoolBeStore) SHALL fall back to unweighted daily average

---

### Requirement: Download failure is non-fatal

If the HTTP download or file parsing fails:
- The store SHALL log a warning.
- All `get_weights()` calls SHALL return `None`.
- The `NordpoolBeStore` SHALL fall back to unweighted averages for any day without weights.
- The integration SHALL continue to function normally.

#### Scenario: Network error during download
- **WHEN** the Synergrid server is unreachable
- **THEN** the store SHALL log a warning and set `available = False`
- **THEN** `store.has_date(today)` SHALL return `False`
- **THEN** NordpoolBeStore SHALL compute an unweighted monthly_average

---

### Requirement: No lifecycle subscriptions

The RLP store has no time-change subscriptions and no cleanup requirements on unload.
`async_stop()` is a no-op (included for symmetry with `NordpoolBeStore`).
