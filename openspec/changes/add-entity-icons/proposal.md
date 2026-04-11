## Why

All entities in the integration currently show a generic default icon in the Home Assistant UI. Adding explicit MDI icons per entity class makes the dashboard immediately scannable — users can visually distinguish tariff inputs, market prices, surcharges, and final all-in prices without reading labels.

## What Changes

- Add `_attr_icon` class attribute to all `NumberEntity` subclasses in `number.py`
- Add `_attr_icon` class attribute to all `SensorEntity` subclasses in `sensor.py`
- No behavior changes — icons are purely cosmetic metadata

## Capabilities

### New Capabilities

- `entity-icons`: MDI icon assignment for all number and sensor entity classes

### Modified Capabilities

<!-- No spec-level requirement changes -->

## Impact

- `custom_components/krowi_energy_management/number.py` — icon added to `KrowiNumberEntity` subclasses (one override per tariff type)
- `custom_components/krowi_energy_management/sensor.py` — icon added to each sensor class
- No API, config entry, or coordinator changes
