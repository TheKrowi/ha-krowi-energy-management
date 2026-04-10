## Why

The component currently depends on the external Nord Pool HACS custom component (`custom_components/nordpool`) to supply electricity spot prices via tracked entity states. This is an uncontrolled dependency — if the Nord Pool component is not installed, updates to its entity IDs, or changes its attribute names, the krowi component silently breaks. Embedding the fetch directly gives full ownership of the data pipeline.

## What Changes

- **NEW** `NordpoolBeStore` — a lightweight store (not a coordinator) that fetches 15-minute day-ahead price slots for region `BE` in `EUR` from the Nord Pool dataportal API. Fetches once per day at startup and once again after 13:00 CET for tomorrow's prices. Dispatches a signal every 15 minutes (at `:01` seconds past each quarter) so sensors update from cached data; no repeated API calls.
- **NEW** `electricity_spot_current_price` sensor — reports the current 15-min slot price in `c€/kWh` (converted from API's `EUR/MWh` by dividing by 10). Exposes `today[]`, `tomorrow[]`, `tomorrow_valid`, `average`, `low_price`, and `price_percent_to_average` as state attributes.
- **NEW** `electricity_spot_average_price` sensor — reports the mean of today's 96 price slots in `c€/kWh`.
- **BREAKING** Electricity config entry removes `current_price_entity` and `fx_rate_entity` fields. These are no longer needed as the component owns the spot price data. Adds `low_price_cutoff` (float, default `1.0`) to the electricity options flow.
- **BREAKING** Config entry migration `v1 → v2` required to drop obsolete fields from existing installs.
- **MODIFIED** `ElectricityImportPriceSensor` — tracks `electricity_spot_current_price` (internal) instead of an external configurable entity. FX conversion logic removed.
- **MODIFIED** Default export template updated to reference `electricity_spot_average_price` instead of an external Nord Pool average entity.

## Capabilities

### New Capabilities

- `nordpool-be-store`: Defines the data store that fetches, caches, and serves 15-minute Nord Pool BE day-ahead price data. Covers API endpoint, fetch schedule, caching strategy, unit conversion (`EUR/MWh → c€/kWh`), and 15-min tick dispatch.
- `electricity-spot-sensors`: Defines the two new electricity spot price sensor entities (`electricity_spot_current_price` and `electricity_spot_average_price`), their state values, attributes, and lifecycle.

### Modified Capabilities

- `electricity-sensors`: Import price formula changes — `current_price` is now sourced from the internal `electricity_spot_current_price` entity (always `c€/kWh`), not a configurable external entity. FX conversion and unit auto-detection requirements are removed.
- `config-flow`: Electricity config entry data shape changes — removes `current_price_entity` and `fx_rate_entity` fields, adds `low_price_cutoff` to options. Config entry version bumps to `2` with a migration step.

## Impact

- **New file**: `custom_components/krowi_energy_management/nordpool_store.py`
- **Modified**: `sensor.py` — new spot sensor classes; import price sensor no longer reads external entity
- **Modified**: `config_flow.py` — electricity setup/options forms; migration handler
- **Modified**: `const.py` — new UIDs for spot sensors, new `CONF_LOW_PRICE_CUTOFF`, drop `CONF_CURRENT_PRICE_ENTITY` / `CONF_FX_RATE_ENTITY` (or keep for gas)
- **Modified**: `manifest.json` — no new dependencies (uses HA's `async_get_clientsession`, stdlib `datetime`, `statistics`)
- **Removed dependency**: `custom_components/nordpool` no longer required; `DEFAULT_ELECTRICITY_PRICE_ENTITY` constant can be removed
