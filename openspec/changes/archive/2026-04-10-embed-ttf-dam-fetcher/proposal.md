## Why

The gas domain currently relies on an external `current_price_entity` (defaulting to `sensor.krowi_ttf_dam_30d_avg` from the separately-installed `krowi_ttf_dam` HACS component). This mirrors the electricity domain's original dependency on the Nord Pool HACS component — a dependency eliminated in the `2026-04-10-embed-nordpool-be-fetcher` change. Embedding the TTF DAM fetch directly into `krowi_energy_management` removes that external dependency, gives full ownership of the gas price pipeline, and eliminates the need for users to install and maintain a separate integration.

Additionally, the gas config entry currently carries a `unit` selector and a `current_price_entity` field that become unnecessary once the store is owned internally. Removing them simplifies the gas config flow and runtime formula, mirroring the `c€/kWh`-always approach used for electricity.

## What Changes

- **NEW** `TtfDamStore` — a lightweight store (not a coordinator) that fetches daily TTF DAM gas prices from the Elindus unauthenticated API (`https://mijn.elindus.be/marketinfo/dayahead/prices?market=GAS&granularity=DAY`). Fetches on startup and resets each day at midnight. Retries every 30 minutes until a data point dated today is present in the response. Converts `EUR/MWh → c€/kWh` at ingest (divide by `10`). Dispatches `SIGNAL_TTF_DAM_UPDATE` after each fetch attempt so sensors update reactively.
- **NEW** `gas_spot_today_price` sensor — reports the latest daily TTF DAM price in `c€/kWh`, sourced directly from the internal store.
- **NEW** `gas_spot_average_price` sensor — reports the 30-day average TTF DAM price in `c€/kWh`, sourced directly from the internal store.
- **BREAKING** Gas config entry removes `unit` and `current_price_entity` fields. Gas unit is now permanently `c€/kWh` (hardcoded constant). No external entity configuration is needed.
- **BREAKING** Config entry migration v2 → v3 strips `unit` and `current_price_entity` from existing gas entries.
- **MODIFIED** `GasCurrentPriceSensor` — sources `current_price` from the internal `gas_spot_today_price` entity (always `c€/kWh`) instead of a configurable external entity. Unit auto-conversion and external entity availability tracking removed.
- **MODIFIED** Gas tariff number entities — `gas_unit` is now the hardcoded constant `c€/kWh` (not read from the config entry).
- **MODIFIED** `gas_current_price_eur` bridge sensor — always converts from `c€/kWh` (divide by 100); gas unit selector scenarios removed.

## Capabilities

### New Capabilities

- `ttf-dam-store`: Defines the `TtfDamStore` — lifecycle, Elindus API fetch, daily refresh strategy (startup + midnight reset + 30-min retry until `data_is_fresh`), ingest conversion (`EUR/MWh → c€/kWh`), and `SIGNAL_TTF_DAM_UPDATE` dispatch.
- `gas-spot-sensors`: Defines the `gas_spot_today_price` and `gas_spot_average_price` sensor entities, their state values, units, and lifecycle.

### Modified Capabilities

- `gas-sensors`: Gas current price formula changes — `current_price` now sourced from internal `gas_spot_today_price` entity (always `c€/kWh`). External entity support, unit auto-conversion, and external unavailability scenarios removed.
- `gas-tariff-entities`: Gas unit is now hardcoded to `c€/kWh`; references to `gas_unit` from the config entry are removed.
- `gas-eur-sensors`: Bridge sensor `gas_current_price_eur` always converts from `c€/kWh`; unit-selector coverage scenarios (`€/kWh`, `€/MWh`) removed.
- `config-flow`: Gas config entry data shape changes — removes `unit` and `current_price_entity` fields. Config entry version bumps to `3` with a v2 → v3 migration step.

## Impact

- **New file**: `custom_components/krowi_energy_management/ttf_dam_store.py`
- **Modified**: `sensor.py` — new gas spot sensor classes; gas current price sensor no longer reads external entity
- **Modified**: `config_flow.py` — gas setup form simplified; migration handler updated to v3
- **Modified**: `const.py` — new UIDs for gas spot sensors, `SIGNAL_TTF_DAM_UPDATE`, hardcoded `GAS_UNIT = "c€/kWh"`; `CONF_CURRENT_PRICE_ENTITY` and gas `CONF_UNIT` removed (or scoped out)
- **Modified**: `number.py` — gas tariff number entities use `GAS_UNIT` constant instead of reading `unit` from the config entry
- **Modified**: `__init__.py` — `TtfDamStore` lifecycle for gas entries; migration v2 → v3; `VERSION = 3`
- **Removed dependency**: `krowi_ttf_dam` HACS component no longer required
