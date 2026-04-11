# Spec: gas-gcv-sensor

## Purpose

Defines the `gas_calorific_value` sensor entity that exposes the monthly Gross Calorific Value for the configured GOS zone, sourced from `GcvStore`.

## Requirements

### Requirement: Gas calorific value sensor
The component SHALL expose a sensor with unique ID `gas_calorific_value`, English display name "Calorific value", and Dutch display name "Calorische waarde" that reports the monthly GCV for the configured GOS zone in `kWh/m³`, sourced from `GcvStore`.

`unit_of_measurement` SHALL be `"kWh/m³"`. `state_class` SHALL be `measurement`. `device_class` SHALL be `None`.

The sensor SHALL subscribe to `SIGNAL_GCV_UPDATE` via `async_dispatcher_connect`. On each signal it SHALL read `store.gcv`. If `store.gcv` is `None`, the sensor state SHALL be `unavailable`.

The sensor SHALL expose an `extra_state_attributes` dict with key `"history"` containing the store's full `{ "YYYY-MM": float }` history dict.

The sensor SHALL expose `data_is_fresh` as an extra state attribute (bool).

#### Scenario: Sensor reports current GCV
- **WHEN** `store.gcv` is `11.5323` (kWh/m³)
- **THEN** `gas_calorific_value` state SHALL be `"11.5323"`

#### Scenario: Sensor reports history attribute
- **WHEN** history contains `{"2026-03": 11.5323, "2026-02": 11.5360}`
- **THEN** `gas_calorific_value` extra state attribute `history` SHALL equal that dict

#### Scenario: Sensor is unavailable before first successful fetch
- **WHEN** `store.gcv` is `None`
- **THEN** `gas_calorific_value` state SHALL be `unavailable`

#### Scenario: Sensor updates when store dispatches signal
- **WHEN** `SIGNAL_GCV_UPDATE` is dispatched and `store.gcv` changes
- **THEN** `gas_calorific_value` SHALL write its new state immediately

#### Scenario: Sensor display name matches language setting
- **WHEN** language is set to `"nl"`
- **THEN** the sensor friendly name SHALL be `"Calorische waarde"`
- **WHEN** language is set to `"en"`
- **THEN** the sensor friendly name SHALL be `"Calorific value"`

#### Scenario: Sensor grouped under Gas device
- **WHEN** the component is loaded
- **THEN** `gas_calorific_value` SHALL be associated with the device identified by `(DOMAIN, entry_id + "_gas")`
