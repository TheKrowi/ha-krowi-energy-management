## ADDED Requirements

### Requirement: Electricity spot RLP-weighted average price sensor
The component SHALL expose a sensor with unique ID `electricity_spot_average_price_rlp`,
English display name "Monthly average price RLP-weighted (EPEX SPOT)", and Dutch display
name "Gewogen maandgemiddelde (EPEX SPOT)" that reports the rolling calendar-month
RLP-weighted average of Nord Pool BE spot prices in `c€/kWh`.

`native_unit_of_measurement` SHALL be `"c€/kWh"`. `state_class` SHALL be
`SensorStateClass.MEASUREMENT`. The sensor SHALL update on every `SIGNAL_NORDPOOL_UPDATE`
dispatch. The sensor SHALL be `unavailable` when `store.monthly_average_rlp` is `None`.

The sensor SHALL expose a `rlp_available` boolean attribute: `True` when all days in the
rolling window had actual RLP weights from `SynergridRLPStore`; `False` when any day fell
back to the unweighted approximation.

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

## MODIFIED Requirements

### Requirement: Spot sensors belong to the electricity device
`electricity_spot_current_price`, `electricity_spot_average_price`, and
`electricity_spot_average_price_rlp` SHALL all be associated with the `DeviceInfo` for the
electricity config entry (identifiers `(DOMAIN, f"{entry_id}_electricity")`).

#### Scenario: Spot sensors appear under the Electricity device in HA
- **WHEN** the electricity config entry is loaded
- **THEN** all three spot sensors SHALL appear under the "Electricity" device in the HA device registry

---

### Requirement: Spot sensors are set up as part of the electricity platform
All three spot sensors SHALL be instantiated in `sensor.py`'s `async_setup_entry` when
`domain_type == DOMAIN_TYPE_ELECTRICITY`.

#### Scenario: Spot sensors present on electricity entry load
- **WHEN** the electricity config entry loads
- **THEN** `electricity_spot_current_price`, `electricity_spot_average_price`, and `electricity_spot_average_price_rlp` SHALL all be registered in HA
