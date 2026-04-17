## MODIFIED Requirements

### Requirement: Supplier export price formula
`electricity_{slug}_export_price` SHALL compute:
`EPEX_monthly_avg_spp × export_multiplier + export_offset`
rounded to 5 decimal places. VAT SHALL NOT be applied (export is BTW-vrij).

`EPEX_monthly_avg_spp` is `NordpoolBeStore.monthly_average_spp` — the SPP-weighted rolling
30-day average in c€/kWh. This replaces the previous use of `monthly_average_rlp` for
export price computation.

If `monthly_average_spp` is `None`, the sensor SHALL be `unavailable`.

#### Scenario: Export price computed with SPP weighting
- **WHEN** `store.monthly_average_spp` is available (e.g. `5.83`)
- **THEN** `electricity_mega_export_price` SHALL equal `round(5.83 × 0.94 + (−1.7), 5)`
- **THEN** no VAT SHALL be applied

#### Scenario: Export sensor unavailable when SPP average missing
- **WHEN** `store.monthly_average_spp` is `None`
- **THEN** `electricity_{slug}_export_price` SHALL be `unavailable`

#### Scenario: Export sensor falls back gracefully when SPP store failed to load
- **WHEN** `SynergridSPPStore` failed to download and `monthly_average_spp` falls back to unweighted average
- **THEN** `electricity_{slug}_export_price` SHALL still produce a value (not unavailable)
- **THEN** a warning SHALL be logged indicating SPP weights were not used
