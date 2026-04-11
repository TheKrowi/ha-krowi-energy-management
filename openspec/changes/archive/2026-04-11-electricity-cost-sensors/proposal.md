## Why

The electricity domain tracks prices but has no way to accumulate actual cost over time. Users with a P1 smart meter (4-register Fluvius: import/export × tariff 1/2) have no cost sensors to feed into HA's Energy Dashboard or automations. Gas already has `gas_total_cost`; electricity needs the equivalent.

## What Changes

- Add 8 new optional config keys to the electricity options flow: 4 meter entity selectors (import/export × tariff 1/2) and 4 price entity selectors (one per meter, defaulting to the existing EUR/kWh price sensors).
- Add 7 new sensor entities to the electricity platform:
  - 4 per-tariff cost/revenue accumulators (`TOTAL_INCREASING`, `RestoreEntity`)
  - 2 derived total sensors (import total, export total) reading live from the 4 accumulators
  - 1 net cost sensor (`MEASUREMENT`) computed as total import cost − total export revenue (can go negative)
- Add default constants for all 8 new config keys to `const.py`.
- Add `NAMES` entries for all 7 new sensors (EN + NL).

## Capabilities

### New Capabilities

- `electricity-cost-sensors`: Accumulated cost sensors for electricity — per-tariff import cost, per-tariff export revenue, total import, total export, and net cost. Backed by configurable P1 meter and price entities.

### Modified Capabilities

- `electricity-tariff-entities`: Options flow gains 8 new entity selector fields for meter and price entities per tariff.

## Impact

- `const.py`: 8 new `CONF_` + `DEFAULT_` constants, 7 new `UID_` constants, 7 × 2 new `NAMES` entries.
- `config_flow.py`: `_electricity_options_schema()` gains 8 new `vol.Optional` `EntitySelector` fields.
- `sensor.py`: 7 new sensor classes + wired into `async_setup_entry` for the electricity domain.
- No version bump needed — all new fields are optional with defaults; existing entries pick them up transparently.
