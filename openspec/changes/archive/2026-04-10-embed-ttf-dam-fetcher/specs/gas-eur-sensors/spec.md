## MODIFIED Requirements

### Requirement: Gas surcharge formula sensor
The component SHALL expose a sensor with unique ID `gas_tariff_total_surcharge_formula` and English display name "Total surcharge formula" that reports a human-readable string showing the four individual gas surcharge values and their sum.

Format: `"<d> + <t> + <e> + <ec> = <total> c€/kWh"` where each value is formatted to 5 decimal places.

`unit_of_measurement` SHALL be `None`. `state_class` SHALL be `None`. The sensor SHALL update reactively whenever any of the four gas tariff rate number entities changes.

#### Scenario: Formula sensor reflects current values
- **WHEN** gas distribution is `1.00000`, transport is `0.50000`, excise duty is `0.30000`, energy contribution is `0.20000`
- **THEN** `gas_tariff_total_surcharge_formula` SHALL report `"1.00000 + 0.50000 + 0.30000 + 0.20000 = 2.00000 c€/kWh"`

#### Scenario: Formula sensor defaults to zeros
- **WHEN** no gas rate has been configured yet
- **THEN** `gas_tariff_total_surcharge_formula` SHALL report `"0.00000 + 0.00000 + 0.00000 + 0.00000 = 0.00000 c€/kWh"`

---

### Requirement: Gas current price EUR/kWh bridge sensor
The component SHALL expose a sensor with unique ID `gas_current_price_eur` and English display name "Current price (EUR/kWh)" that reports `gas_current_price` converted to `EUR/kWh`.

`unit_of_measurement` SHALL be `"EUR/kWh"`. `state_class` SHALL be `measurement`. Value SHALL be rounded to 5 decimal places.

Since gas unit is always `c€/kWh`, the conversion is always: divide `gas_current_price` by `100`.

#### Scenario: EUR bridge converts from c€/kWh
- **WHEN** `gas_current_price` is `6.16253` (c€/kWh)
- **THEN** `gas_current_price_eur` SHALL be `0.06163` (rounded to 5 decimal places)

#### Scenario: EUR bridge is unavailable when gas price is unavailable
- **WHEN** `gas_current_price` is `unavailable`
- **THEN** `gas_current_price_eur` SHALL be `unavailable`

## REMOVED Requirements

### Requirement: Gas EUR bridge converts from €/kWh
**Reason**: Gas unit is now hardcoded to `c€/kWh`. The `€/kWh` and `€/MWh` conversion branches in the bridge sensor are removed.
**Migration**: Users previously using `€/kWh` or `€/MWh` as gas unit will have their config entries migrated to `c€/kWh`. Values in the bridge sensor may differ numerically but represent the same physical price.

### Requirement: Gas EUR bridge converts from €/MWh
**Reason**: Same as above.
**Migration**: Same as above.
