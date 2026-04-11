## Why

Gas meters in Belgium measure consumption in m³, but the integration only exposes prices and sensors in c€/kWh. The missing link is the Gross Calorific Value (GCV) — a monthly, zone-specific conversion factor (kWh/m³) published by Atrias. Without it, users must hardcode a stale estimate (e.g. 10.35 from the L-gas era) that is now ~12% wrong since Belgium completed its H-gas transition.

## What Changes

- **New store `GcvStore`**: fetches the Atrias GCV API monthly, persists a 12-month rolling history in HA storage, and dispatches `SIGNAL_GCV_UPDATE`.
- **New config options on the gas entry**: GOS zone selector (dropdown, default `GOS FLUVIUS - LEUVEN`) and gas meter entity selector (default `sensor.gas_meter_consumption`).
- **New sensor `gas_calorific_value`**: exposes the live GCV for the configured GOS zone in kWh/m³, with a 12-month history attribute.
- **New sensor `gas_current_price_m3`**: gas price in €/m³ = `gas_current_price_eur × gas_calorific_value`.
- **New sensor `gas_consumption_kwh`**: gas consumption in kWh = `gas_meter_m³ × gas_calorific_value`. Suitable for the HA energy dashboard.

## Capabilities

### New Capabilities

- `gcv-store`: Internal store that fetches, persists, and serves the monthly Atrias GCV for the configured GOS zone.
- `gas-gcv-sensor`: Sensor exposing the live calorific value (kWh/m³) with 12-month history attribute.
- `gas-m3-sensors`: Two new sensors derived from the GCV: gas price in €/m³ and gas consumption in kWh.

### Modified Capabilities

- `gas-tariff-entities`: GOS zone selector and gas meter entity config options added to the gas options flow.

## Impact

- **New file**: `gcv_store.py` — mirrors `ttf_dam_store.py` pattern.
- **`sensor.py`**: three new sensor classes for `gas_calorific_value`, `gas_current_price_m3`, `gas_consumption_kwh`.
- **`const.py`**: new constants `CONF_GOS_ZONE`, `CONF_GAS_METER_ENTITY`, `SIGNAL_GCV_UPDATE`, `DEFAULT_GOS_ZONE`, `DEFAULT_GAS_METER_ENTITY`, `ATRIAS_GCV_API_URL`, `ATRIAS_SUBSCRIPTION_KEY`, and new UID suffixes.
- **`config_flow.py`**: GOS zone dropdown and gas meter entity selector added to the gas options flow.
- **`__init__.py`**: `GcvStore` lifecycle (start/stop) wired into the gas config entry setup/unload.
- **External dependency**: Atrias API (`api.atrias.be`) — unauthenticated aside from a public subscription key embedded in the URL.
