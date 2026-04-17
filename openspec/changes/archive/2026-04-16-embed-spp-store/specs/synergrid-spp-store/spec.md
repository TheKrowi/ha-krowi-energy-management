## ADDED Requirements

### Requirement: SPP store downloads and caches the annual Synergrid SPP ex-ante profile
The component SHALL maintain a `SynergridSPPStore` instance for the lifetime of the
integration. On `async_start()` the store SHALL attempt to load cached weights from HA
Storage. If the current date is not present in the cache, it SHALL download
`SPP_ex-ante_and_ex-post_{year}.xlsx` from:

```
https://www.synergrid.be/images/downloads/SLP-RLP-SPP/{year}/SPP_ex-ante_and_ex-post_{year}.xlsx
```

The file SHALL be parsed using only stdlib (`zipfile` + `xml.etree.ElementTree`). No new
manifest requirement is needed. Parsing SHALL be delegated to `hass.async_add_executor_job`.

Parsed data is stored as `dict[str, list[float]]` mapping ISO date strings (`YYYY-MM-DD`)
to a list of exactly 96 `SPPExanteBE` weight floats in chronological QH order. On DST
spring-forward days the row sequence skips H=2 (96 rows still present, H=2 absent).

The sheet containing ex-ante data SHALL be located by name (`SPP_ex-ante_{year}`) by
parsing `xl/workbook.xml` and resolving its `rId` via `xl/_rels/workbook.xml.rels`.

Parsed weights SHALL be persisted to HA Storage under key
`krowi_energy_management_spp_{year}`.

#### Scenario: Store loads from cache on startup
- **WHEN** the integration loads and today's date is present in HA Storage
- **THEN** no download SHALL occur
- **THEN** `spp_store.available` SHALL be `True`
- **THEN** `spp_store.get_weights(date.today())` SHALL return a list of 96 floats

#### Scenario: Store downloads on cache miss
- **WHEN** the integration loads and today's date is not in HA Storage
- **THEN** the store SHALL download the annual SPP xlsx from Synergrid
- **THEN** the parsed weights SHALL be persisted to HA Storage
- **THEN** `spp_store.available` SHALL be `True`

#### Scenario: Download fails gracefully
- **WHEN** the Synergrid URL returns an HTTP error or times out
- **THEN** `spp_store.available` SHALL be `False`
- **THEN** the integration SHALL continue loading without error

#### Scenario: Weights retrieved for a specific date
- **WHEN** `spp_store.get_weights(date(2026, 4, 16))` is called and that date is cached
- **THEN** the method SHALL return a list of 96 floats
- **THEN** night-time slots (H=0 through H=6) SHALL all be `0.0`
- **THEN** midday slots (around H=12–13) SHALL have the highest values

#### Scenario: Weights unavailable for a date
- **WHEN** `spp_store.get_weights(d)` is called for a date not in the cache
- **THEN** the method SHALL return `None`
