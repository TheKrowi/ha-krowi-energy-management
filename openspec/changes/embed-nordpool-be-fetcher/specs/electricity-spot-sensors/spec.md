## ADDED Requirements

### Requirement: Electricity spot current price sensor
The component SHALL expose a sensor with unique ID `electricity_spot_current_price` and English display name "Spot current price" that reports the Nord Pool BE current 15-minute slot price in `c€/kWh`.

`native_unit_of_measurement` SHALL be `"c€/kWh"`. `state_class` SHALL be `SensorStateClass.MEASUREMENT`. The sensor SHALL update on every `SIGNAL_NORDPOOL_UPDATE` dispatch. The sensor SHALL be `unavailable` when `store.current_price` is `None`.

#### Scenario: Sensor reports current slot price
- **WHEN** the 15-min tick fires and `store.current_price = 7.692`
- **THEN** `electricity_spot_current_price` state SHALL be `7.692`

#### Scenario: Sensor is unavailable when store has no data
- **WHEN** `store.current_price` is `None` (e.g. API failed on startup)
- **THEN** `electricity_spot_current_price` state SHALL be `unavailable`

#### Scenario: Sensor state attributes are populated
- **WHEN** `store.data_today` contains 96 slots and `store.data_tomorrow` contains 96 slots
- **THEN** the sensor's `extra_state_attributes` SHALL contain:
  - `today`: list of 96 float values in chronological order
  - `tomorrow`: list of 96 float values in chronological order
  - `tomorrow_valid`: `True`
  - `average`: mean of today's 96 values rounded to 5 decimal places
  - `low_price`: bool
  - `price_percent_to_average`: float rounded to 5 decimal places

#### Scenario: Tomorrow attributes when not yet available
- **WHEN** `store.tomorrow_valid` is `False`
- **THEN** `tomorrow` attribute SHALL be `[]`
- **THEN** `tomorrow_valid` attribute SHALL be `False`

#### Scenario: Sensor updates at each 15-min boundary
- **WHEN** the clock advances from `00:14:59` to `00:15:01`
- **THEN** `electricity_spot_current_price` SHALL update to the value of the `00:15–00:30` slot

---

### Requirement: Electricity spot average price sensor
The component SHALL expose a sensor with unique ID `electricity_spot_average_price` and English display name "Spot average price" that reports the mean of all today's Nord Pool BE price slots in `c€/kWh`.

`native_unit_of_measurement` SHALL be `"c€/kWh"`. `state_class` SHALL be `SensorStateClass.MEASUREMENT`. The sensor SHALL update on every `SIGNAL_NORDPOOL_UPDATE` dispatch. The sensor SHALL be `unavailable` when `store.average` is `None`.

#### Scenario: Sensor reports today's average
- **WHEN** the store has a full 96-slot dataset with `average = 10.41200`
- **THEN** `electricity_spot_average_price` state SHALL be `10.41200`

#### Scenario: Sensor is unavailable when store has no data
- **WHEN** `store.average` is `None`
- **THEN** `electricity_spot_average_price` state SHALL be `unavailable`

#### Scenario: Average updates at midnight when new day data is loaded
- **WHEN** the midnight fetch completes with a new day's prices
- **THEN** `electricity_spot_average_price` SHALL update to the new day's mean value

---

### Requirement: Spot sensors belong to the electricity device
Both `electricity_spot_current_price` and `electricity_spot_average_price` SHALL be associated with the `DeviceInfo` for the electricity config entry (identifiers `(DOMAIN, f"{entry_id}_electricity")`).

#### Scenario: Spot sensors appear under the Electricity device in HA
- **WHEN** the electricity config entry is loaded
- **THEN** both spot sensors SHALL appear under the "Electricity" device in the HA device registry

---

### Requirement: Spot sensors are set up as part of the electricity platform
Both spot sensors SHALL be instantiated in `sensor.py`'s `async_setup_entry` when `domain_type == DOMAIN_TYPE_ELECTRICITY`. They SHALL be added alongside the existing electricity sensors.

#### Scenario: Spot sensors present on electricity entry load
- **WHEN** the electricity config entry loads
- **THEN** `electricity_spot_current_price` and `electricity_spot_average_price` SHALL both be registered in HA
