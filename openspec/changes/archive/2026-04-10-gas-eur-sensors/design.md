## Context

The gas device already has `gas_tariff_total_surcharge` (sum of four rate entities) and `gas_current_price` (formula-based price sensor). Electricity has two additional sensors not yet present on gas: a human-readable formula string and a `EUR/kWh` bridge used by the HA Energy Dashboard. This design adds both.

The existing `convert_unit()` utility in `utils.py` already handles `c€/kWh ↔ €/kWh ↔ €/MWh` conversions. The EUR bridge can reuse it directly.

## Goals / Non-Goals

**Goals:**
- Add `GasSurchargeFormulaSensor` — exact mirror of `ElectricitySurchargeFormulaSensor` over gas rate entities.
- Add `GasCurrentPriceEurSensor` — reads `gas_current_price`, converts to `EUR/kWh` via `convert_unit()`, always outputs `EUR/kWh`.

**Non-Goals:**
- No FX rate support for gas (TTF DAM prices are always in €/MWh; no currency conversion needed).
- No config flow changes.
- No `EUR/m³` conversion — gas is tracked in energy units throughout this component.

## Decisions

### Decision: EUR bridge uses `convert_unit()` from `utils.py`

`convert_unit(value, source_unit, "EUR/kWh")` where `source_unit` is `gas_unit`. This reuses the same logic as `GasCurrentPriceSensor` already uses when reading the upstream price entity, keeping unit conversion in one place.

Alternative considered: hard-code divisors (`÷ 100`, `÷ 1`, `÷ 1000`) per `gas_unit` value. Rejected — `convert_unit()` already encodes the same logic and keeps behaviour consistent.

### Decision: Formula sensor is a pure string sensor (no unit, no state_class)

Identical stance to `ElectricitySurchargeFormulaSensor`. A diagnostic/display entity; no numeric processing by HA.

### Decision: `gas_current_price_eur` subscribes to `gas_current_price` state changes

Mirrors `ElectricityImportPriceEurSensor` — resolves the source entity via `_resolve_entity_id()` and tracks it with `async_track_state_change_event`. No need to re-read the individual tariff entities.

## Risks / Trade-offs

- [Risk] If `gas_unit` is `c€/kWh` and `convert_unit()` doesn't recognise `c€/kWh` as a valid source for `EUR/kWh`, the bridge returns `None`. → Mitigation: `convert_unit()` already handles this path; verified in existing electricity bridge.
- [Risk] If `gas_current_price` itself is `unavailable`, `GasCurrentPriceEurSensor` must also go unavailable. → Mitigation: `safe_float_state` returns `None` on unavailable; guard sets `native_value = None`.
