## MODIFIED Requirements

### Requirement: Electricity spot current price sensor
The component SHALL expose a sensor with unique ID `electricity_spot_current_price`, English display name "Current price (EPEX SPOT)", and Dutch display name "Huidige prijs (EPEX SPOT)" that reports the Nord Pool BE current 15-minute slot price in `c€/kWh`.

`native_unit_of_measurement` SHALL be `"c€/kWh"`. `state_class` SHALL be `SensorStateClass.MEASUREMENT`. The sensor SHALL update on every `SIGNAL_NORDPOOL_UPDATE` dispatch. The sensor SHALL be `unavailable` when `store.current_price` is `None`.

#### Scenario: Sensor reports current slot price
- **WHEN** the 15-min tick fires and `store.current_price = 7.692`
- **THEN** `electricity_spot_current_price` state SHALL be `7.692`

#### Scenario: Sensor is unavailable when store has no data
- **WHEN** `store.current_price` is `None` (e.g. API failed on startup)
- **THEN** `electricity_spot_current_price` state SHALL be `unavailable`

#### Scenario: Sensor display name matches language setting
- **WHEN** language is set to `"nl"`
- **THEN** the sensor friendly name SHALL be `"Huidige prijs (EPEX SPOT)"`
- **WHEN** language is set to `"en"`
- **THEN** the sensor friendly name SHALL be `"Current price (EPEX SPOT)"`

---

### Requirement: Electricity spot average price sensor
The component SHALL expose a sensor with unique ID `electricity_spot_average_price`, English display name "Daily average price (EPEX SPOT)", and Dutch display name "Gemiddelde dagprijs (EPEX SPOT)" that reports the mean of all today's Nord Pool BE price slots in `c€/kWh`.

`native_unit_of_measurement` SHALL be `"c€/kWh"`. `state_class` SHALL be `SensorStateClass.MEASUREMENT`. The sensor SHALL update on every `SIGNAL_NORDPOOL_UPDATE` dispatch. The sensor SHALL be `unavailable` when `store.average` is `None`.

#### Scenario: Sensor reports today's average
- **WHEN** the store has a full 96-slot dataset with `average = 10.41200`
- **THEN** `electricity_spot_average_price` state SHALL be `10.41200`

#### Scenario: Sensor is unavailable when store has no data
- **WHEN** `store.average` is `None`
- **THEN** `electricity_spot_average_price` state SHALL be `unavailable`

#### Scenario: Sensor display name matches language setting
- **WHEN** language is set to `"nl"`
- **THEN** the sensor friendly name SHALL be `"Gemiddelde dagprijs (EPEX SPOT)"`
- **WHEN** language is set to `"en"`
- **THEN** the sensor friendly name SHALL be `"Daily average price (EPEX SPOT)"`
