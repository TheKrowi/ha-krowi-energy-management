## MODIFIED Requirements

### Requirement: Electricity import price sensor
The component SHALL expose a sensor with unique ID `electricity_current_price_import` and English display name "Current import price" that computes the current electricity import price.

Formula: `(spot_price + surcharge) * (1 + vat / 100)`, rounded to 5 decimal places.

Where:
- `spot_price` is the state of `electricity_spot_current_price` (always `c€/kWh`)
- `surcharge` is the state of `electricity_tariff_total_surcharge` (always `c€/kWh`)
- `vat` is the state of `electricity_vat` (in %)

`unit_of_measurement` SHALL be `"c€/kWh"`. `state_class` SHALL be `measurement`.

The sensor SHALL track state changes on `electricity_spot_current_price`, `electricity_tariff_total_surcharge`, and `electricity_vat`.

#### Scenario: Import price computed correctly
- **WHEN** `electricity_spot_current_price` is `9.079` (c€/kWh), surcharge is `5.442` (c€/kWh), VAT is `21.0%`
- **THEN** import price SHALL be `(9.079 + 5.442) * 1.21 = 17.57002` (rounded to 5 decimal places)

#### Scenario: Import price is unavailable when spot price is unavailable
- **WHEN** `electricity_spot_current_price` is `unavailable` or `unknown`
- **THEN** `electricity_current_price_import` state SHALL be `unavailable`

#### Scenario: Import price updates when spot price changes
- **WHEN** `electricity_spot_current_price` changes to a new value on a 15-min tick
- **THEN** `electricity_current_price_import` SHALL recompute immediately

## REMOVED Requirements

### Requirement: Nord Pool unit auto-converted from MWh to kWh
**Reason**: The electricity domain no longer reads an external `current_price_entity`. The `NordpoolBeStore` converts `EUR/MWh → c€/kWh` at ingest time. No runtime unit detection or conversion is needed in the sensor.
**Migration**: No user action required. The import price sensor now always receives `c€/kWh` from `electricity_spot_current_price`.

### Requirement: FX conversion applied when configured
**Reason**: The electricity domain no longer reads an external `current_price_entity`, so there is no foreign-currency source to convert. The `fx_rate_entity` field is removed from the electricity config entry.
**Migration**: Users who had configured `fx_rate_entity` will need to handle FX conversion externally if required. The component is designed for EUR-denominated Belgian electricity prices.

### Requirement: Import price is unavailable when FX sensor is unavailable
**Reason**: Removed alongside the FX conversion feature.
**Migration**: No user action required.

### Requirement: Unit not recognised
**Reason**: Removed alongside the external `current_price_entity` and unit-detection logic.
**Migration**: No user action required.
