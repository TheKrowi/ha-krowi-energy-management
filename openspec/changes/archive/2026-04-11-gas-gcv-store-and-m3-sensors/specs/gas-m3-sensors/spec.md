## ADDED Requirements

### Requirement: Gas price per m³ sensor
The component SHALL expose a sensor with unique ID `gas_current_price_m3`, English display name "Current price (€/m³)", and Dutch display name "Huidige prijs (€/m³)" that reports the current gas price in `€/m³`.

Formula: `gas_current_price_eur × gas_calorific_value`, rounded to 5 decimal places.

Where:
- `gas_current_price_eur` is `sensor.krowi_energy_management_gas_current_price_eur` (EUR/kWh)
- `gas_calorific_value` is read from `GcvStore.gcv` (kWh/m³)

`unit_of_measurement` SHALL be `"€/m³"`. `state_class` SHALL be `measurement`. `device_class` SHALL be `None`.

The sensor SHALL track state changes on `gas_current_price_eur` and SHALL re-read `store.gcv` on each update. If either value is unavailable, the sensor state SHALL be `unavailable`.

#### Scenario: Price per m³ computed correctly
- **WHEN** `gas_current_price_eur` is `0.06163` (EUR/kWh) and `store.gcv` is `11.5323`
- **THEN** `gas_current_price_m3` SHALL be `0.06163 × 11.5323 = 0.71090` (rounded to 5 decimal places)

#### Scenario: Sensor unavailable when EUR price is unavailable
- **WHEN** `gas_current_price_eur` is `unavailable`
- **THEN** `gas_current_price_m3` state SHALL be `unavailable`

#### Scenario: Sensor unavailable when GCV is not yet fetched
- **WHEN** `store.gcv` is `None`
- **THEN** `gas_current_price_m3` state SHALL be `unavailable`

#### Scenario: Sensor updates when EUR price changes
- **WHEN** `gas_current_price_eur` changes state
- **THEN** `gas_current_price_m3` SHALL recompute immediately

#### Scenario: Sensor grouped under Gas device
- **WHEN** the component is loaded
- **THEN** `gas_current_price_m3` SHALL be associated with the device identified by `(DOMAIN, entry_id + "_gas")`

---

### Requirement: Gas consumption in kWh sensor
The component SHALL expose a sensor with unique ID `gas_consumption_kwh`, English display name "Consumption (kWh)", and Dutch display name "Verbruik (kWh)" that reports gas consumption converted from m³ to kWh.

Formula: `gas_meter_m3 × gas_calorific_value`, rounded to 3 decimal places.

Where:
- `gas_meter_m3` is the state of the entity configured in `CONF_GAS_METER_ENTITY` (m³, total_increasing)
- `gas_calorific_value` is read from `GcvStore.gcv` (kWh/m³)

`unit_of_measurement` SHALL be `"kWh"`. `state_class` SHALL be `total_increasing`. `device_class` SHALL be `SensorDeviceClass.ENERGY`.

The sensor SHALL track state changes on the entity identified by `CONF_GAS_METER_ENTITY`. If the gas meter entity state is unavailable, unknown, or not parseable as float, the sensor state SHALL be `unavailable`. If `store.gcv` is `None`, the sensor state SHALL be `unavailable`.

`CONF_GAS_METER_ENTITY` defaults to `"sensor.gas_meter_consumption"`. If `CONF_GAS_METER_ENTITY` is `None` or empty, the sensor state SHALL be `unavailable`.

#### Scenario: Consumption computed correctly
- **WHEN** `sensor.gas_meter_consumption` is `1234.567` (m³) and `store.gcv` is `11.5323`
- **THEN** `gas_consumption_kwh` SHALL be `1234.567 × 11.5323 = 14,236.xxx` rounded to 3 decimal places

#### Scenario: Sensor unavailable when meter entity is unavailable
- **WHEN** `CONF_GAS_METER_ENTITY` state is `unavailable`
- **THEN** `gas_consumption_kwh` state SHALL be `unavailable`

#### Scenario: Sensor unavailable when GCV not yet fetched
- **WHEN** `store.gcv` is `None`
- **THEN** `gas_consumption_kwh` state SHALL be `unavailable`

#### Scenario: Sensor unavailable when no meter entity configured
- **WHEN** `CONF_GAS_METER_ENTITY` is `None` or empty string
- **THEN** `gas_consumption_kwh` state SHALL be `unavailable`

#### Scenario: Sensor updates when meter reading changes
- **WHEN** `CONF_GAS_METER_ENTITY` changes state
- **THEN** `gas_consumption_kwh` SHALL recompute immediately

#### Scenario: Sensor suitable for HA energy dashboard
- **WHEN** the component is loaded
- **THEN** `gas_consumption_kwh` SHALL have `state_class = total_increasing` and `device_class = energy`
- **THEN** it SHALL be selectable as a gas source in the HA energy dashboard

#### Scenario: Sensor grouped under Gas device
- **WHEN** the component is loaded
- **THEN** `gas_consumption_kwh` SHALL be associated with the device identified by `(DOMAIN, entry_id + "_gas")`
