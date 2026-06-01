## Why

The Atrias GCV API subscription key is hardcoded in `const.py`. If Atrias ever rotates this key, fixing it requires a new HACS release; users cannot self-recover. Making the key configurable via the gas options flow eliminates this dependency on a code release.

## What Changes

- Add `CONF_ATRIAS_SUBSCRIPTION_KEY` config key to the gas options flow, pre-filled with the known public default.
- `GcvStore.async_start()` gains a `subscription_key` parameter and uses it instead of the module-level constant.
- `__init__.py` reads the key from the gas entry's effective options and passes it to `async_start()`.

## Capabilities

### New Capabilities

- `gcv-subscription-key`: Atrias GCV API subscription key is exposed as a configurable gas option, pre-filled with the known default value, changeable at any time via the gas entry's options flow without requiring a restart beyond the normal options-flow reload.

### Modified Capabilities

_(none — no existing spec-level requirements change)_

## Impact

- `custom_components/krowi_energy_management/const.py` — add `CONF_ATRIAS_SUBSCRIPTION_KEY`
- `custom_components/krowi_energy_management/config_flow.py` — add field to `_gas_options_schema()`
- `custom_components/krowi_energy_management/__init__.py` — read key from effective options, pass to `GcvStore.async_start()`
- `custom_components/krowi_energy_management/gcv_store.py` — accept and use `subscription_key` in `async_start()`
