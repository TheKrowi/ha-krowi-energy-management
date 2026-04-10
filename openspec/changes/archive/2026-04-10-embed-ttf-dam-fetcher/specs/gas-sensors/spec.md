## MODIFIED Requirements

### Requirement: Gas current price sensor
The component SHALL expose a sensor with unique ID `gas_current_price` and English display name "Current price" that computes the current gas price.

Formula: `(spot_price + surcharge) * (1 + vat / 100)`, rounded to 5 decimal places.

Where:
- `spot_price` is the state of `gas_spot_today_price` (always `c€/kWh`)
- `surcharge` is the state of `gas_tariff_total_surcharge` (always `c€/kWh`)
- `vat` is the state of `gas_vat` (in %)

`unit_of_measurement` SHALL be `"c€/kWh"`. `state_class` SHALL be `measurement`.

The sensor SHALL track state changes on `gas_spot_today_price`, `gas_tariff_total_surcharge`, and `gas_vat`.

#### Scenario: Gas price computed correctly
- **WHEN** `gas_spot_today_price` is `4.543` (c€/kWh), gas surcharge is `0.55` (c€/kWh), VAT is `21.0%`
- **THEN** gas price SHALL be `(4.543 + 0.55) * 1.21 = 6.16253` (rounded to 5 decimal places)

#### Scenario: Gas price is unavailable when spot price is unavailable
- **WHEN** `gas_spot_today_price` is `unavailable` or `unknown`
- **THEN** `gas_current_price` state SHALL be `unavailable`

#### Scenario: Gas price updates when spot price changes
- **WHEN** `gas_spot_today_price` changes after a daily store refresh
- **THEN** `gas_current_price` SHALL recompute immediately

## REMOVED Requirements

### Requirement: Gas current price entity auto-converted from MWh to kWh
**Reason**: The gas domain no longer reads an external `current_price_entity`. The `TtfDamStore` converts `EUR/MWh → c€/kWh` at ingest. No runtime unit detection or conversion is needed in the sensor.
**Migration**: No user action required. The gas current price sensor now always receives `c€/kWh` from `gas_spot_today_price`.

### Requirement: Gas current price entity auto-converted from kWh to MWh
**Reason**: Same as above — no external entity to convert.
**Migration**: No user action required.

### Requirement: Gas price is unavailable when current price entity is unavailable
**Reason**: Replaced by the new "unavailable when spot price is unavailable" scenario above.
**Migration**: No user action required.

### Requirement: Current price entity unit not recognised
**Reason**: Removed alongside external `current_price_entity` and unit-detection logic.
**Migration**: No user action required.
