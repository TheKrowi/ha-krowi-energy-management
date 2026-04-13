## Why

The electricity import/export price sensors currently use formulas that are not tied to any
real supplier contract. To accurately track what Mega (or any other EPEX-indexed supplier)
actually charges, we need supplier-specific price sensors with the correct formulas hardcoded
per supplier. Multiple suppliers can be added simultaneously to enable comparison and
contract switching without breaking any existing automations or dashboards.

The EPEX monthly average used in supplier formulas is defined by Mega (and other Belgian
variable-rate suppliers) as the **RLP-weighted** quarterly mean. We now fetch the annual
Synergrid RLP0N profile to compute this exactly, eliminating the previous ~2-3% approximation
from an unweighted mean.

This is Phase 1: add the RLP store, improve the monthly average, add supplier sensors.
Existing sensors are untouched.

## What Changes

- Add `SynergridRLPStore` (`rlp_store.py`) that downloads and caches the annual Synergrid
  RLP0N electricity profile; add `pyxlsb>=1.0.10` to `manifest.json` requirements.
- Update `NordpoolBeStore` to accept an `SynergridRLPStore` reference; change the daily
  average buffer from `dict[date, float]` to `dict[date, tuple[float, float]]`
  (`weighted_sum`, `weight_sum`); update `monthly_average` to use RLP-weighted formula.
- Add a new `DOMAIN_TYPE_ELECTRICITY_SUPPLIER` config entry type.
- Add `ELECTRICITY_SUPPLIER_CATALOG` to `const.py` with `mega` as the first entry.
- Add a supplier config flow step: pick supplier from catalog + optional label override.
- Add 4 new sensor entities per supplier config entry:
  - `electricity_{slug}_import_price` (c€/kWh, incl. VAT)
  - `electricity_{slug}_import_price_eur` (EUR/kWh, incl. VAT)
  - `electricity_{slug}_export_price` (c€/kWh, BTW-vrij)
  - `electricity_{slug}_export_price_eur` (EUR/kWh, BTW-vrij)
- The existing electricity sensors, tariff numbers, and cost sensors are **not modified**.

## Capabilities

### New Capabilities

- `synergrid-rlp-store`: Annual RLP0N profile download and cache; provides per-slot weights.
- `supplier-price-sensors`: Supplier-specific electricity price sensors computed from the
  RLP-weighted EPEX monthly average with supplier-specific multipliers and offsets.

### Modified Capabilities

- `nordpool-be-store`: `monthly_average` is now RLP-weighted instead of an unweighted mean.
  Backward-compatible migration of the existing buffer (old entries treated as unweighted,
  self-heal within ~30 days).

## Impact

- `manifest.json`: Add `"pyxlsb>=1.0.10"` to `requirements`.
- `rlp_store.py`: New file — `SynergridRLPStore` class.
- `__init__.py`: Instantiate and start `SynergridRLPStore` before `NordpoolBeStore`; pass
  the RLP store reference to `NordpoolBeStore.async_start()`.
- `nordpool_store.py`: Accept `SynergridRLPStore` in `async_start()`; update
  `_snapshot_today()` and `monthly_average` for RLP weighting; migrate old buffer entries.
- `const.py`: Add `DOMAIN_TYPE_ELECTRICITY_SUPPLIER`, `CONF_SUPPLIER_SLUG`,
  `CONF_SUPPLIER_LABEL`, `ELECTRICITY_SUPPLIER_CATALOG`, 4 UID pattern constants,
  and `NAMES` entries for all 4 sensor types × all supported suppliers × all languages.
- `config_flow.py`: Add supplier branch to `async_step_user`; add
  `async_step_electricity_supplier` collecting slug + label.
- `sensor.py`: Add 4 new sensor classes
  (`ElectricitySupplierImportPriceSensor`, `ElectricitySupplierImportPriceEurSensor`,
  `ElectricitySupplierExportPriceSensor`, `ElectricitySupplierExportPriceEurSensor`)
  and wire them into `async_setup_entry` for the supplier domain type.
- No changes to `number.py` or existing sensor classes.
- No version bump required — fully additive.
