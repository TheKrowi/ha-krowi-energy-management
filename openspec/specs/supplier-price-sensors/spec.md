# Spec: supplier-price-sensors

## Purpose

Defines the architecture for supplier-specific electricity price sensors and the proxy (active-supplier) layer that sits between them and the cost accounting sensors.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  RAW MARKET DATA (stable, supplier-agnostic, unchanged)         │
│  sensor.electricity_spot_current_price   ← EPEX 15-min slot     │
│  sensor.electricity_spot_average_price   ← EPEX monthly avg     │
└─────────────────────────────────────────────────────────────────┘
             │                        │
             ▼                        ▼
┌────────────────────────┐  ┌────────────────────────┐
│  SUPPLIER: mega        │  │  SUPPLIER: eneco        │
│  electricity_mega_     │  │  electricity_eneco_     │
│    import_price        │  │    import_price         │
│    import_price_eur    │  │    import_price_eur     │
│    export_price        │  │    export_price         │
│    export_price_eur    │  │    export_price_eur     │
└────────────────────────┘  └────────────────────────┘
             │
             │  ← "current supplier = mega"
             ▼
┌─────────────────────────────────────────────────────────────────┐
│  PROXY sensors (stable IDs, follow current supplier)            │
│  sensor.electricity_current_price_import                        │
│  sensor.electricity_current_price_import_eur                    │
│  sensor.electricity_current_price_export                        │
│  sensor.electricity_current_price_export_eur                    │
└─────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│  COST sensors (stable, already use configurable price entity)   │
│  sensor.electricity_import_cost_tariff_1 / _2                   │
│  sensor.electricity_export_revenue_tariff_1 / _2                │
│  sensor.electricity_total_import_cost                           │
│  sensor.electricity_total_export_revenue                        │
│  sensor.electricity_net_cost                                    │
└─────────────────────────────────────────────────────────────────┘
```

## Layers

### Layer 1 — Raw Market Data

`sensor.electricity_spot_current_price` and `sensor.electricity_spot_average_price` are
purely market data sensors. They are supplier-agnostic: no supplier formula is applied.
Their entity IDs are permanent and will never move to a supplier-specific namespace.

### Layer 2 — Supplier Config Entries

Each supplier is a separate HA config entry with `domain_type = "electricity_supplier"`.
The config entry stores:
- `supplier_slug` — machine-readable key matching a catalog entry (e.g. `"mega"`).
- `supplier_label` — human-readable override for the device name (e.g. `"Mega jan 2025"`).

Each supplier config entry creates exactly 4 sensor entities:

| Unique ID pattern                        | Unit      | VAT applied |
|------------------------------------------|-----------|-------------|
| `electricity_{slug}_import_price`        | `c€/kWh`  | yes         |
| `electricity_{slug}_import_price_eur`    | `EUR/kWh` | yes         |
| `electricity_{slug}_export_price`        | `c€/kWh`  | no (exempt) |
| `electricity_{slug}_export_price_eur`    | `EUR/kWh` | no (exempt) |

The slug is used verbatim in the unique ID and entity ID. If the user provides a custom
label it becomes the device name only; the entity IDs are always slug-based.

### Layer 3 — Proxy Sensors (Active Supplier)

The electricity config entry exposes a `select.electricity_current_supplier` entity.
Its options are the set of currently configured supplier slugs, plus `"none"`.

The 4 proxy sensors watch the select entity and mirror the active supplier's corresponding
sensor. When `current_supplier = "none"` the proxy sensors are `unavailable`.

The proxy sensors keep their existing entity IDs permanently:
- `sensor.electricity_current_price_import`
- `sensor.electricity_current_price_import_eur`
- `sensor.electricity_current_price_export`
- `sensor.electricity_current_price_export_eur`

### Layer 4 — Cost Sensors

Cost sensors remain unchanged. They already accept configurable price entity IDs via the
options flow. They will continue to reference the proxy sensor IDs (which is the default).
Switching the active supplier automatically propagates through to cost accounting.

## Implementation Phases

### Phase 1 — Supplier config entries and supplier-specific sensors
Add `DOMAIN_TYPE_ELECTRICITY_SUPPLIER`. Implement the supplier catalog in `const.py`.
Add the supplier config flow. Create the 4 supplier sensor entities per supplier.
Existing sensors are **not modified**. Proxy sensors are **not yet implemented**.
Users can add Mega and verify formula correctness independently.

### Phase 2 — Active supplier selection and proxy sensors
Add `select.electricity_current_supplier` to the electricity config entry.
Convert the existing import/export price sensors into proxy sensors that mirror the
active supplier. Retire `CONF_EXPORT_TEMPLATE`.

## Supplier Catalog

Defined in `const.py` as `ELECTRICITY_SUPPLIER_CATALOG`. Each entry has:

```python
{
    "name": str,                      # Display name (e.g. "Mega")
    "import": {
        "epex_multiplier": float,     # Applied to monthly EPEX average before surcharge
        "epex_offset_cEur_kwh": float,# Added to EPEX after multiplier (usually 0.0)
        "includes_surcharge": bool,   # True = formula already includes regulatory costs
        "vat_exempt": bool,           # False for import
    },
    "export": {
        "epex_multiplier": float,     # Applied to monthly EPEX average
        "epex_offset_cEur_kwh": float,# Subtracted fixed component (negative = deduction)
        "includes_surcharge": bool,   # False for export (no regulatory costs)
        "vat_exempt": bool,           # True for export (BTW-vrij)
    },
}
```

### Mega (slug: `mega`)

Import formula (excl. BTW, source: Mega tariefkaart 12/2025):
```
import_excl_btw = (EPEX_monthly_avg × 1.061) + surcharge
import_incl_btw = import_excl_btw × (1 + VAT/100)
```

Export formula (excl. BTW, BTW-vrij):
```
export = EPEX_monthly_avg × 0.94 − 1.7  (c€/kWh)
```

Where:
- `EPEX_monthly_avg` = `sensor.electricity_spot_average_price_rlp` (c€/kWh, RLP-weighted monthly mean)
- `surcharge` = `sensor.electricity_tariff_total_surcharge` (c€/kWh)
- `VAT` = `number.electricity_vat` (%)

`electricity_spot_average_price_rlp` delivers the proper RLP-weighted monthly mean via
`NordpoolBeStore.monthly_average_rlp`; see specs `synergrid-rlp-store`, `nordpool-be-store`,
and `electricity-spot-sensors` for how the Synergrid RLP0N weights are fetched and applied.
`sensor.electricity_spot_average_price` (unweighted) remains a valid independent measurement
and is not used in supplier formulas.

## Requirements

### Requirement: Supplier catalog defined in const.py
`const.py` SHALL define `ELECTRICITY_SUPPLIER_CATALOG: dict[str, dict]` mapping supplier
slugs to formula parameters. `"mega"` SHALL be the first catalog entry.

### Requirement: Supplier config entry creates 4 sensor entities
A config entry with `domain_type = "electricity_supplier"` SHALL create exactly 4 sensor
entities using the slug from `CONF_SUPPLIER_SLUG`. The entities SHALL be assigned to a
`DeviceInfo` named after the supplier label.

### Requirement: Supplier import price formula
`electricity_{slug}_import_price` SHALL compute:
`(EPEX_monthly_avg × import_multiplier + import_offset + surcharge) × (1 + VAT/100)`
rounded to 5 decimal places.

The sensor SHALL be `unavailable` when `electricity_spot_average_price` is unavailable.

### Requirement: Supplier export price formula
`electricity_{slug}_export_price` SHALL compute:
`EPEX_monthly_avg_spp × export_multiplier + export_offset`
rounded to 5 decimal places. VAT SHALL NOT be applied (export is BTW-vrij).

`EPEX_monthly_avg_spp` is `NordpoolBeStore.monthly_average_spp` — the SPP-weighted rolling
30-day average in c€/kWh. This replaces the previous use of `monthly_average_rlp` for
export price computation.

If `monthly_average_spp` is `None`, the sensor SHALL be `unavailable`.

#### Scenario: Export price computed with SPP weighting
- **WHEN** `store.monthly_average_spp` is available (e.g. `5.83`)
- **THEN** `electricity_mega_export_price` SHALL equal `round(5.83 × 0.94 + (−1.7), 5)`
- **THEN** no VAT SHALL be applied

#### Scenario: Export sensor unavailable when SPP average missing
- **WHEN** `store.monthly_average_spp` is `None`
- **THEN** `electricity_{slug}_export_price` SHALL be `unavailable`

#### Scenario: Export sensor falls back gracefully when SPP store failed to load
- **WHEN** `SynergridSPPStore` failed to download and `monthly_average_spp` falls back to unweighted average
- **THEN** `electricity_{slug}_export_price` SHALL still produce a value (not unavailable)
- **THEN** a warning SHALL be logged indicating SPP weights were not used

### Requirement: EUR/kWh bridge sensors
`electricity_{slug}_import_price_eur` SHALL be `import_price ÷ 100`.
`electricity_{slug}_export_price_eur` SHALL be `export_price ÷ 100`.
Both SHALL track state changes on their source sensor.

### Requirement: Proxy sensors (Phase 2)
Defined separately in spec `supplier-active-selection`.
