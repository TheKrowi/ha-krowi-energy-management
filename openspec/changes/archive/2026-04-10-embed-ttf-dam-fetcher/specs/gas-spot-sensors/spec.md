## ADDED Requirements

### Requirement: Gas spot today price sensor
The component SHALL expose a sensor with unique ID `gas_spot_today_price` and English display name "Spot today price" that reports the latest daily TTF DAM price in `c€/kWh`, sourced from the internal `TtfDamStore`.

`unit_of_measurement` SHALL be `"c€/kWh"`. `state_class` SHALL be `measurement`. `device_class` SHALL be `None`.

The sensor SHALL subscribe to `SIGNAL_TTF_DAM_UPDATE` via `async_dispatcher_connect`. On each signal it SHALL read `store.today_price`. If `store.today_price` is `None`, the sensor state SHALL be `unavailable`.

#### Scenario: Sensor reports today's price when store is fresh
- **WHEN** `store.today_price` is `4.543` (c€/kWh)
- **THEN** `gas_spot_today_price` state SHALL be `"4.543"`

#### Scenario: Sensor is unavailable before first successful fetch
- **WHEN** `store.today_price` is `None` (no successful fetch yet)
- **THEN** `gas_spot_today_price` state SHALL be `unavailable`

#### Scenario: Sensor updates when store dispatches signal
- **WHEN** `SIGNAL_TTF_DAM_UPDATE` is dispatched and `store.today_price` changes
- **THEN** `gas_spot_today_price` SHALL write its new state immediately

---

### Requirement: Gas spot average price sensor
The component SHALL expose a sensor with unique ID `gas_spot_average_price` and English display name "Spot 30-day average" that reports the 30-day average TTF DAM price in `c€/kWh`, sourced from the internal `TtfDamStore`.

`unit_of_measurement` SHALL be `"c€/kWh"`. `state_class` SHALL be `measurement`. `device_class` SHALL be `None`.

The sensor SHALL subscribe to `SIGNAL_TTF_DAM_UPDATE` via `async_dispatcher_connect`. On each signal it SHALL read `store.average`. If `store.average` is `None`, the sensor state SHALL be `unavailable`.

#### Scenario: Sensor reports 30-day average when store has data
- **WHEN** `store.average` is `5.29` (c€/kWh)
- **THEN** `gas_spot_average_price` state SHALL be `"5.29"`

#### Scenario: Sensor is unavailable before first successful fetch
- **WHEN** `store.average` is `None`
- **THEN** `gas_spot_average_price` state SHALL be `unavailable`

---

### Requirement: Gas spot sensors grouped under Gas device
Both `gas_spot_today_price` and `gas_spot_average_price` SHALL return a `DeviceInfo` that places them under the shared Gas device.

The device identifier SHALL be `(DOMAIN, f"{entry_id}_gas")`.

#### Scenario: Gas spot sensors belong to Gas device
- **WHEN** the component is loaded
- **THEN** both gas spot sensor entities SHALL be associated with the device identified by `(DOMAIN, entry_id + "_gas")`
