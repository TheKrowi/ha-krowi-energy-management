## ADDED Requirements

### Requirement: NordpoolBeStore maintains an SPP-weighted daily buffer
`NordpoolBeStore` SHALL accept an optional `spp_store: SynergridSPPStore | None` parameter
in `async_start()`. It SHALL maintain `_daily_spp_buffer: dict[date, tuple[float, float]]`
storing `(weighted_sum, weight_total)` tuples, parallel to `_daily_rlp_buffer`. The buffer
SHALL be persisted to HA Storage under key
`krowi_energy_management_nordpool_daily_spp_avg`.

#### Scenario: SPP buffer populated at midnight snapshot
- **WHEN** the clock reaches 00:00:01 and `self.average` is not `None`
- **THEN** `_snapshot_today()` SHALL compute an SPP entry for yesterday and store it in `_daily_spp_buffer`
- **THEN** the SPP buffer SHALL be persisted to HA Storage alongside the RLP buffer

#### Scenario: SPP buffer trimmed with RLP buffer
- **WHEN** `_trim_buffer()` is called
- **THEN** all entries older than `date.today() - relativedelta(months=1)` SHALL be removed from `_daily_spp_buffer`

#### Scenario: SPP buffer backfilled on startup
- **WHEN** the integration loads and `_daily_spp_buffer` is missing dates in the rolling window
- **THEN** `_async_backfill()` SHALL fetch those dates and populate `_daily_spp_buffer` for each

### Requirement: NordpoolBeStore exposes a monthly_average_spp property
`NordpoolBeStore` SHALL expose a `monthly_average_spp` property that computes the
SPP-weighted rolling 30-day average in c€/kWh, rounded to 5 decimal places. The
computation SHALL use `_daily_spp_buffer` entries plus a live SPP entry for today,
following the same weighted-sum / weight-total formula as `monthly_average_rlp`.

If `SynergridSPPStore` is unavailable or returns `None` weights for a day, that day's
contribution SHALL fall back to unweighted (equal weights across all slots).

#### Scenario: SPP average computed correctly
- **WHEN** `spp_store.get_weights(d)` returns valid 96-slot weights for all days in the window
- **THEN** `monthly_average_spp` SHALL equal `sum(price_i × spp_i) / sum(spp_i)` across all slots in the rolling window
- **THEN** the result SHALL differ from `monthly_average_rlp` (profiles differ)

#### Scenario: SPP average falls back to unweighted when weights unavailable
- **WHEN** `spp_store` is `None` or `get_weights()` returns `None` for a day
- **THEN** that day's contribution SHALL use equal weights (same as unweighted daily average)
- **THEN** `monthly_average_spp` SHALL still return a non-`None` value if `self.average` is available
