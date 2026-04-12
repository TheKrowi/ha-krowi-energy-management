## Context

Cost/revenue accumulator sensors (`_ElectricityTariffCostSensor` subclasses, `GasTotalCostSensor`) and the derived aggregate sensors (`ElectricityTotalImportCostSensor`, `ElectricityTotalExportRevenueSensor`, `ElectricityNetCostSensor`) were implemented in separate changes without a governing icon spec. Each sensor received an ad hoc `mdi:cash-*` icon. The entity-icons spec covers tariff numbers, surcharge sensors, and price sensors — but not accumulated monetary outcome sensors.

## Goals / Non-Goals

**Goals:**
- Replace the 8 ad hoc icons with a consistent `mdi:invoice-text-*` family
- Extend `entity-icons` spec to formally cover the accumulated cost/revenue sensor layer
- Establish the three-layer icon model as the documented convention

**Non-Goals:**
- Changing icons on any other sensor or number entity
- Modifying sensor logic, units, state class, or behaviour of any kind
- Introducing new sensors or capabilities

## Decisions

### Use `mdi:invoice-text-*` family for all outcome sensors

**Decision:** All accumulated cost/revenue sensors use icons from the `invoice-text` family.

**Rationale:** An invoice is the natural metaphor for a monetary outcome — it represents the result of energy consumption or generation, not a rate or a configuration input. The family provides three meaningful variants:

| Variant | Meaning | Used for |
|---|---|---|
| `mdi:invoice-text-plus` | Revenue / incoming money | export revenue sensors |
| `mdi:invoice-text-minus` | Cost / outgoing money | import cost sensors |
| `mdi:invoice-text` | Net / neutral | net cost + gas total cost |

**Alternatives considered:**
- `mdi:receipt-text` — similar semantics but less common in HA ecosystem
- `mdi:cash-multiple` (current) — generic, no directional semantics
- `mdi:currency-eur` — conflates "price per unit" with "accumulated total"

### Base class does not carry the icon

**Decision:** Each concrete sensor class declares its own `_attr_icon`. The `_ElectricityTariffCostSensor` base class keeps `mdi:cash-multiple` replaced by no default — each subclass sets its own.

**Rationale:** Import cost and export revenue sensors require different icons despite sharing the same base class. A base-class default would need to be overridden anyway, adding noise.

## Risks / Trade-offs

- **No runtime risk** — `_attr_icon` is a static class attribute. HA reads it at entity registration; changing it requires only a HA restart or entity reload to take effect.
- **No migration needed** — Icons are not persisted; they resolve fresh on every HA startup.

## Open Questions

_(none — fully resolved in explore session)_
