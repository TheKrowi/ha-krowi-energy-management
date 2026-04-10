## Why

When three config entries exist (`electricity`, `gas`, `settings`), `__init__.py` forwards all three to the `number` and `sensor` platforms. The settings entry is never supposed to register any entities, but it leaks through and registers a duplicate set of gas number entities because `number.async_setup_entry` branches `if electricity / else gas` — the settings entry falls through the `else` branch. This produces phantom entities in the UI with no real backing data.

## What Changes

- Guard platform forwarding in `async_setup_entry` and `async_unload_entry` so only `electricity` and `gas` entries touch `Platform.NUMBER` / `Platform.SENSOR`.
- Tighten `number.async_setup_entry` to use `if/elif/else: return` instead of a bare `else`, preventing any unknown domain type from silently registering gas entities.
- Apply the same `if/elif/else: return` guard in `sensor.async_setup_entry` for consistency.

## Capabilities

### New Capabilities

_(none — this is a bug fix)_

### Modified Capabilities

- `config-flow`: The settings entry contract now explicitly excludes platform entity registration. No user-facing behavior changes; spec updated to document this invariant.

## Impact

- `custom_components/krowi_energy_management/__init__.py` — `async_setup_entry` and `async_unload_entry`
- `custom_components/krowi_energy_management/number.py` — `async_setup_entry`
- `custom_components/krowi_energy_management/sensor.py` — `async_setup_entry`
