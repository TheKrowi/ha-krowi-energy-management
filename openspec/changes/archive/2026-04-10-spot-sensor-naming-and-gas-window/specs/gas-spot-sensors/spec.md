## MODIFIED Requirements

### Requirement: Gas spot today price sensor
The component SHALL expose a sensor with unique ID `gas_spot_today_price`, English display name "Daily price (TTF DAM)", and Dutch display name "Dagprijs (TTF DAM)" that reports the latest daily TTF DAM price in `c€/kWh`, sourced from the internal `TtfDamStore`.

`unit_of_measurement` SHALL be `"c€/kWh"`. `state_class` SHALL be `measurement`. `device_class` SHALL be `None`.

The sensor SHALL subscribe to `SIGNAL_TTF_DAM_UPDATE` via `async_dispatcher_connect`. On each signal it SHALL read `store.today_price`. If `store.today_price` is `None`, the sensor state SHALL be `unavailable`.

#### Scenario: Sensor reports today's price when store is fresh
- **WHEN** `store.today_price` is `4.543` (c€/kWh)
- **THEN** `gas_spot_today_price` state SHALL be `"4.543"`

#### Scenario: Sensor is unavailable before first successful fetch
- **WHEN** `store.today_price` is `None` (no successful fetch yet)
- **THEN** `gas_spot_today_price` state SHALL be `unavailable`

#### Scenario: Sensor display name matches language setting
- **WHEN** language is set to `"nl"`
- **THEN** the sensor friendly name SHALL be `"Dagprijs (TTF DAM)"`
- **WHEN** language is set to `"en"`
- **THEN** the sensor friendly name SHALL be `"Daily price (TTF DAM)"`

---

### Requirement: Gas spot average price sensor
The component SHALL expose a sensor with unique ID `gas_spot_average_price`, English display name "Monthly average price (TTF DAM)", and Dutch display name "Gemiddelde maandprijs (TTF DAM)" that reports the rolling calendar-month average TTF DAM price in `c€/kWh`, sourced from the internal `TtfDamStore`.

`unit_of_measurement` SHALL be `"c€/kWh"`. `state_class` SHALL be `measurement`. `device_class` SHALL be `None`.

The sensor SHALL subscribe to `SIGNAL_TTF_DAM_UPDATE` via `async_dispatcher_connect`. On each signal it SHALL read `store.average`. If `store.average` is `None`, the sensor state SHALL be `unavailable`.

#### Scenario: Sensor reports monthly average when store has data
- **WHEN** `store.average` is `5.29` (c€/kWh)
- **THEN** `gas_spot_average_price` state SHALL be `"5.29"`

#### Scenario: Sensor is unavailable before first successful fetch
- **WHEN** `store.average` is `None`
- **THEN** `gas_spot_average_price` state SHALL be `unavailable`

#### Scenario: Sensor display name matches language setting
- **WHEN** language is set to `"nl"`
- **THEN** the sensor friendly name SHALL be `"Gemiddelde maandprijs (TTF DAM)"`
- **WHEN** language is set to `"en"`
- **THEN** the sensor friendly name SHALL be `"Monthly average price (TTF DAM)"`
