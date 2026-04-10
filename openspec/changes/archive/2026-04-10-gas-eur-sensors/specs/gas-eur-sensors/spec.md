## ADDED Requirements

### Requirement: Gas surcharge formula sensor
The component SHALL expose a sensor with unique ID `gas_tariff_total_surcharge_formula` and English display name "Total surcharge formula" that reports a human-readable string showing the four individual gas surcharge values and their sum.

Format: `"<d> + <t> + <e> + <ec> = <total> <unit>"` where each value is formatted to 5 decimal places.

`unit_of_measurement` SHALL be `None`. `state_class` SHALL be `None`. The sensor SHALL update reactively whenever any of the four gas tariff rate number entities changes.

#### Scenario: Formula sensor reflects current values
- **WHEN** gas distribution is `1.00000`, transport is `0.50000`, excise duty is `0.30000`, energy contribution is `0.20000`, and `gas_unit` is `€/MWh`
- **THEN** `gas_tariff_total_surcharge_formula` SHALL report `"1.00000 + 0.50000 + 0.30000 + 0.20000 = 2.00000 €/MWh"`

#### Scenario: Formula sensor defaults to zeros
- **WHEN** no gas rate has been configured yet
- **THEN** `gas_tariff_total_surcharge_formula` SHALL report `"0.00000 + 0.00000 + 0.00000 + 0.00000 = 0.00000 <gas_unit>"`

#### Scenario: Formula sensor updates when a rate changes
- **WHEN** any of the four gas tariff rate entities changes state
- **THEN** `gas_tariff_total_surcharge_formula` SHALL recompute immediately

---

### Requirement: Gas current price EUR/kWh bridge sensor
The component SHALL expose a sensor with unique ID `gas_current_price_eur` and English display name "Current price (EUR/kWh)" that reports `gas_current_price` converted to `EUR/kWh`.

`unit_of_measurement` SHALL be `"EUR/kWh"`. `state_class` SHALL be `measurement`. Value SHALL be rounded to 5 decimal places.

Conversion from `gas_unit` to `EUR/kWh`:
- `c€/kWh` → divide by `100`
- `€/kWh` → no conversion (factor `1`)
- `€/MWh` → divide by `1000`

#### Scenario: EUR bridge converts from c€/kWh
- **WHEN** `gas_current_price` is `10.00000` and `gas_unit` is `c€/kWh`
- **THEN** `gas_current_price_eur` SHALL be `0.10000`

#### Scenario: EUR bridge converts from €/kWh
- **WHEN** `gas_current_price` is `0.07500` and `gas_unit` is `€/kWh`
- **THEN** `gas_current_price_eur` SHALL be `0.07500`

#### Scenario: EUR bridge converts from €/MWh
- **WHEN** `gas_current_price` is `70.66400` and `gas_unit` is `€/MWh`
- **THEN** `gas_current_price_eur` SHALL be `0.07066` (rounded to 5 decimal places)

#### Scenario: EUR bridge is unavailable when gas price is unavailable
- **WHEN** `gas_current_price` is `unavailable`
- **THEN** `gas_current_price_eur` SHALL be `unavailable`

#### Scenario: EUR bridge grouped under Gas device
- **WHEN** the component is loaded
- **THEN** `gas_current_price_eur` SHALL be associated with the device identified by `(DOMAIN, entry_id + "_gas")`
