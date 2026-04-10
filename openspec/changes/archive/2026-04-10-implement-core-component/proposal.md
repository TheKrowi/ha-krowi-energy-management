## Why

The `krowi_energy_management` Home Assistant custom component does not yet exist as a codebase. The OpenAPI spec and design decisions have been agreed on but no Python code has been written. This change delivers the full initial implementation so the component can be installed via HACS and used in a real HA instance.

## What Changes

- **New**: HACS-compatible custom component at `custom_components/krowi_energy_management/`
- **New**: `ConfigFlow` — multi-step menu-based setup; user picks a domain (Electricity / Gas) then fills domain-specific fields; each installed domain becomes its own config entry; duplicate domains are blocked
- **New**: `OptionsFlow` per entry — shows only the fields relevant to that domain; pre-populates current values; triggers full entry reload on save
- **New**: 5 electricity tariff `NumberEntity` (RestoreNumber) — editable rates persisted across restarts; initial value 0
- **New**: 5 gas tariff `NumberEntity` (RestoreNumber) — same persistence behaviour; initial value 0
- **New**: 4 electricity computed `SensorEntity` — total surcharge rate, surcharge formula string, import price, export price (Jinja2 template rendered fully reactively via `async_track_template_result`)
- **New**: 2 gas computed `SensorEntity` — total gas surcharge, current gas price
- **New**: Runtime unit auto-conversion for upstream sources — reads `unit_of_measurement` attribute from Nord Pool and TTF DAM entities at runtime; auto-scales across kWh/MWh/Wh; applies optional FX multiplier from a configurable sensor entity
- **New**: Unavailability propagation — any computed sensor becomes `unavailable` if a required upstream entity is unavailable or missing

## Capabilities

### New Capabilities

- `config-flow`: Multi-entry config flow — HA menu step domain picker, per-domain config entry data shapes, duplicate prevention, domain-aware options flow, reload-on-save behaviour
- `electricity-tariff-entities`: Five electricity tariff number entities (green energy contribution, distribution & transport, excise duty, energy contribution, VAT); RestoreNumber persistence; electricity unit from config
- `gas-tariff-entities`: Five gas tariff number entities (distribution, transport/Fluxys, excise duty, energy contribution, VAT); RestoreNumber persistence; gas unit from config
- `electricity-sensors`: Four computed electricity sensors (total surcharge, surcharge formula string, import price, export price); runtime Nord Pool unit detection, magnitude auto-scaling, optional FX conversion; reactive template rendering for export price
- `gas-sensors`: Two computed gas sensors (total gas surcharge, current gas price); runtime TTF DAM unit detection, magnitude auto-scaling to configured gas unit

### Modified Capabilities

<!-- none — this is the initial implementation, no existing specs -->

## Impact

- **New files**: All files under `custom_components/krowi_energy_management/` plus `hacs.json` at repo root
- **Dependencies**: `nordpool` HA custom component (external, not managed here); `krowi_ttf_dam` companion component (separate repo)
- **HA version**: Targets current stable HA; uses standard `NumberEntity`, `SensorEntity`, `RestoreNumber`, `async_track_state_change_event`, `async_track_template_result`
- **No breaking changes** — first implementation
