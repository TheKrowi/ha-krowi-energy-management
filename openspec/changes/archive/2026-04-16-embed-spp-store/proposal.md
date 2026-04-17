## Why

The export price formula used by Belgian variable-rate suppliers (e.g. Mega) is weighted
by the **Synergrid SPP** (Synthetisch Productieprofiel) — a solar PV production profile —
not RLP. The current export sensors use `monthly_average_rlp` as a fallback, which
overestimates the export price because RLP weights evening/morning consumption peaks while
SPP concentrates weight around midday when solar production (and day-ahead prices) are lower.
Implementing SPP weighting corrects this and makes the export sensors faithful to the Mega
formula.

## What Changes

- **New**: `SynergridSPPStore` — downloads, parses and caches the Synergrid SPP ex-ante
  annual profile (`SPP_ex-ante_and_ex-post_{year}.xlsx`) using stdlib only (no new dependency).
- **New**: `NordpoolBeStore.monthly_average_spp` property — SPP-weighted rolling 30-day
  average in c€/kWh, parallel to the existing `monthly_average_rlp`.
- **Modified**: `ElectricitySupplierExportPriceSensor` — switches its base EPEX value from
  `monthly_average_rlp` to `monthly_average_spp`.
- **No changes** to import sensors, config flow, entity IDs, or manifest requirements.

## Capabilities

### New Capabilities

- `synergrid-spp-store`: Downloads and caches the Synergrid SPP ex-ante profile. Provides
  per-QH (15-min) solar production weights for Belgium. Feeds a new SPP-weighted monthly
  average into `NordpoolBeStore`.

### Modified Capabilities

- `nordpool-be-store`: New `monthly_average_spp` property, SPP buffer, and SPP snapshot
  logic alongside the existing RLP equivalents.
- `supplier-price-sensors`: Export formula source corrected from RLP-weighted to
  SPP-weighted monthly average.

## Impact

- **New file**: `custom_components/krowi_energy_management/spp_store.py`
- **Modified**: `nordpool_store.py` — new buffer, property, snapshot, trim, backfill hooks
- **Modified**: `sensor.py` — export sensor uses `monthly_average_spp`
- **Modified**: `__init__.py` — wire `SynergridSPPStore` into `NordpoolBeStore.async_start()`
- **No manifest changes** — SPP file is parsed with stdlib `zipfile` + `xml.etree.ElementTree`
