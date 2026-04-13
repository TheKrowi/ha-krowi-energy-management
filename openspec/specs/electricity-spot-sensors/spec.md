# Spec: electricity-spot-sensors

## Purpose

Defines the electricity spot price sensor entities that expose the internally-fetched Nord Pool BE day-ahead prices: current slot price and today's average price.

## Requirements

### Requirement: Electricity spot current price sensor
The component SHALL expose a sensor with unique ID `electricity_spot_current_price`, English display name "Current price (EPEX SPOT)", and Dutch display name "Huidige prijs (EPEX SPOT)" that reports the Nord Pool BE current 15-minute slot price in `c€/kWh`.

`native_unit_of_measurement` SHALL be `"c€/kWh"`. `state_class` SHALL be `SensorStateClass.MEASUREMENT`. The sensor SHALL update on every `SIGNAL_NORDPOOL_UPDATE` dispatch. The sensor SHALL be `unavailable` when `store.current_price` is `None`.

The sensor's `extra_state_attributes` SHALL contain: `today`, `tomorrow`, `tomorrow_valid`, `low_price`, `price_percent_to_average`. The `average` attribute SHALL NOT be present.

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

#### Scenario: Sensor state attributes are populated without average
- **WHEN** `store.data_today` contains 96 slots and `store.data_tomorrow` contains 96 slots
- **THEN** the sensor's `extra_state_attributes` SHALL contain `today`, `tomorrow`, `tomorrow_valid`, `low_price`, `price_percent_to_average`
- **THEN** `extra_state_attributes` SHALL NOT contain an `average` key

#### Scenario: Tomorrow attributes when not yet available
- **WHEN** `store.tomorrow_valid` is `False`
- **THEN** `tomorrow` attribute SHALL be `[]`
- **THEN** `tomorrow_valid` attribute SHALL be `False`

#### Scenario: Sensor updates at each 15-min boundary
- **WHEN** the clock advances from `00:14:59` to `00:15:01`
- **THEN** `electricity_spot_current_price` SHALL update to the value of the `00:15–00:30` slot

---

### Requirement: Electricity spot average price sensor
The component SHALL expose a sensor with unique ID `electricity_spot_average_price`, English display name "Monthly average price (EPEX SPOT)", and Dutch display name "Gemiddelde maandprijs (EPEX SPOT)" that reports the rolling calendar-month average of Nord Pool BE spot prices in `c€/kWh`.

`native_unit_of_measurement` SHALL be `"c€/kWh"`. `state_class` SHALL be `SensorStateClass.MEASUREMENT`. The sensor SHALL update on every `SIGNAL_NORDPOOL_UPDATE` dispatch. The sensor SHALL be `unavailable` when `store.monthly_average` is `None`.

The sensor SHALL expose a `history` attribute containing the completed-day buffer as a dict mapping `"YYYY-MM-DD"` ISO strings to `float` values in `c€/kWh`, covering the calendar-month window excluding today.

#### Scenario: Sensor reports monthly average
- **WHEN** the store has a full 30-day buffer and today's live average is `9.50000`
- **THEN** `electricity_spot_average_price` state SHALL be `store.monthly_average`

#### Scenario: Sensor is unavailable when store has no data
- **WHEN** `store.monthly_average` is `None`
- **THEN** `electricity_spot_average_price` state SHALL be `unavailable`

#### Scenario: Sensor display name matches language setting
- **WHEN** language is set to `"nl"`
- **THEN** the sensor friendly name SHALL be `"Gemiddelde maandprijs (EPEX SPOT)"`
- **WHEN** language is set to `"en"`
- **THEN** the sensor friendly name SHALL be `"Monthly average price (EPEX SPOT)"`

#### Scenario: Monthly average updates intraday as today's prices evolve
- **WHEN** the 15-min tick fires and `store.average` changes
- **THEN** `electricity_spot_average_price` SHALL update to reflect the new `store.monthly_average`

#### Scenario: History attribute contains completed days
- **WHEN** `store._daily_avg_buffer` contains entries for `2026-03-12` through `2026-04-10`
- **THEN** the `history` attribute SHALL be `{"2026-03-12": 8.45123, ..., "2026-04-10": 9.87600}`
- **THEN** today's date SHALL NOT appear as a key in `history`

---

### Requirement: Electricity spot RLP-weighted average price sensor
The component SHALL expose a sensor with unique ID `electricity_spot_average_price_rlp`,
English display name "Monthly average price RLP-weighted (EPEX SPOT)", and Dutch display
name "Gewogen maandgemiddelde (EPEX SPOT)" that reports the rolling calendar-month
**RLP-weighted** average of Nord Pool BE spot prices in `c€/kWh`.

`native_unit_of_measurement` SHALL be `"c€/kWh"`. `state_class` SHALL be
`SensorStateClass.MEASUREMENT`. The sensor SHALL update on every `SIGNAL_NORDPOOL_UPDATE`
dispatch. The sensor SHALL be `unavailable` when `store.monthly_average_rlp` is `None`.

The sensor SHALL expose a `rlp_available` boolean attribute: `True` when all days in the
rolling window have actual RLP weights from `SynergridRLPStore`; `False` when any day
fell back to the unweighted approximation.

#### Scenario: Sensor reports RLP-weighted monthly average
- **WHEN** the store has a full 30-day RLP buffer and today's weighted average is available
- **THEN** `electricity_spot_average_price_rlp` state SHALL be `store.monthly_average_rlp`

#### Scenario: Sensor is unavailable when store has no data
- **WHEN** `store.monthly_average_rlp` is `None`
- **THEN** `electricity_spot_average_price_rlp` state SHALL be `unavailable`

#### Scenario: RLP attribute reflects weight availability
- **WHEN** all days in the window have weights from `SynergridRLPStore`
- **THEN** `rlp_available` SHALL be `True`
- **WHEN** one or more days fell back to unweighted
- **THEN** `rlp_available` SHALL be `False`

---

### Requirement: Spot sensors belong to the electricity device
Both `electricity_spot_current_price`, `electricity_spot_average_price`, and
`electricity_spot_average_price_rlp` SHALL be associated with the `DeviceInfo` for the
electricity config entry (identifiers `(DOMAIN, f"{entry_id}_electricity")`).

#### Scenario: Spot sensors appear under the Electricity device in HA
- **WHEN** the electricity config entry is loaded
- **THEN** both spot sensors SHALL appear under the "Electricity" device in the HA device registry

---

### Requirement: Spot sensors are set up as part of the electricity platform
All three spot sensors SHALL be instantiated in `sensor.py`'s `async_setup_entry` when
`domain_type == DOMAIN_TYPE_ELECTRICITY`. They SHALL be added alongside the existing
electricity sensors.

#### Scenario: Spot sensors present on electricity entry load
- **WHEN** the electricity config entry loads
- **THEN** `electricity_spot_current_price`, `electricity_spot_average_price`, and
  `electricity_spot_average_price_rlp` SHALL all be registered in HA
