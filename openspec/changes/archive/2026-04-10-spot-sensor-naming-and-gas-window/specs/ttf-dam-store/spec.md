## MODIFIED Requirements

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
