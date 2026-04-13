## ADDED Requirements

### Requirement: RLP store downloads and parses annual profile on startup
On `async_start(hass)`, the store SHALL attempt to load persisted data from HA Storage.
If today's date is not covered (first install, year rollover, or corrupt cache), the store
SHALL download `RLP0N {YEAR} Electricity.xlsb` from Synergrid and parse it using `pyxlsb`
via `hass.async_add_executor_job`. Parsed data SHALL be persisted back to HA Storage.

Download URL pattern:
`https://www.synergrid.be/images/downloads/SLP-RLP-SPP/{YEAR}/RLP0N%20{YEAR}%20Electricity.xlsb`

Parsed data model: `dict[date, list[float]]` — 96 weight floats per calendar day
(92 on DST spring-forward, 100 on fall-back).

Persisted under HA Storage key: `krowi_energy_management_rlp_{year}`

#### Scenario: First startup, no persisted data
- **WHEN** no HA Storage data exists for the current year
- **THEN** the store SHALL download the annual `.xlsb` file
- **THEN** `store.has_date(today)` SHALL return `True` after parsing

#### Scenario: Startup with valid persisted data
- **WHEN** HA Storage contains valid data and today's date is present
- **THEN** the store SHALL NOT make any HTTP request
- **THEN** `store.has_date(today)` SHALL return `True`

#### Scenario: Year rollover
- **WHEN** today is January 1 and stored data covers the previous year
- **THEN** the store SHALL download the new year's file

#### Scenario: Network error during download
- **WHEN** the Synergrid server is unreachable
- **THEN** the store SHALL log a warning and set `available = False`
- **THEN** `store.has_date(today)` SHALL return `False`

---

### Requirement: RLP store exposes per-day weights
The store SHALL expose:
- `store.get_weights(d: date) -> list[float] | None` — returns 96-entry weight list or `None`
- `store.has_date(d: date) -> bool` — returns `True` iff weights are cached for `d`

#### Scenario: Weights available
- **WHEN** `store.has_date(date(2026, 4, 10))` is `True`
- **THEN** `store.get_weights(date(2026, 4, 10))` SHALL return a list of 96 floats

#### Scenario: Weights not available
- **WHEN** download failed or date is outside the year
- **THEN** `store.get_weights(d)` SHALL return `None`

---

### Requirement: Download failure is non-fatal
If HTTP download or file parsing fails, the store SHALL log a warning, set `available = False`,
and return `None` for all `get_weights()` calls. The integration SHALL continue normally.
`NordpoolBeStore` SHALL fall back to unweighted contributions for any day without weights.

#### Scenario: Integration works without RLP data
- **WHEN** `SynergridRLPStore.available` is `False`
- **THEN** `NordpoolBeStore.monthly_average_rlp` SHALL still return a value using unweighted fallback

---

### Requirement: No lifecycle subscriptions
`async_stop()` on `SynergridRLPStore` is a no-op. No time-change subscriptions.
The store has no cleanup requirements on integration unload.

#### Scenario: Store stopped
- **WHEN** `async_stop()` is called
- **THEN** no errors are raised and no listeners need to be cancelled
