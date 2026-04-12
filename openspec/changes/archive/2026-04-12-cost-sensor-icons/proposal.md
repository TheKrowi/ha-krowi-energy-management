## Why

Cost, revenue, and net-cost sensors were implemented without icon specifications — they received ad hoc `mdi:cash-*` icons that lack consistent semantics and are not covered by the entity-icons spec. This change formalises a three-layer icon model (tariff inputs → prices → monetary outcomes) and aligns implementation to that model.

## What Changes

- Update `sensor.py` icons for 8 accumulated-cost/revenue sensors:
  - `electricity_export_revenue_tariff_1` → `mdi:invoice-text-plus`
  - `electricity_export_revenue_tariff_2` → `mdi:invoice-text-plus`
  - `electricity_total_export_revenue` → `mdi:invoice-text-plus`
  - `electricity_import_cost_tariff_1` → `mdi:invoice-text-minus`
  - `electricity_import_cost_tariff_2` → `mdi:invoice-text-minus`
  - `electricity_total_import_cost` → `mdi:invoice-text-minus`
  - `electricity_net_cost` → `mdi:invoice-text`
  - `gas_total_cost` → `mdi:invoice-text`
- Extend `entity-icons` spec with requirements covering accumulated cost/revenue sensors.

## Capabilities

### New Capabilities
_(none — this change extends an existing capability only)_

### Modified Capabilities
- `entity-icons`: Add requirements for accumulated cost/revenue sensor icons (import cost, export revenue, net cost, gas total cost).

## Impact

- `custom_components/krowi_energy_management/sensor.py` — 8 `_attr_icon` values changed
- `openspec/specs/entity-icons/spec.md` — new requirements added
