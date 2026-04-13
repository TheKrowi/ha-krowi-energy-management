## 1. Dependencies

- [x] 1.1 Add `"pyxlsb>=1.0.10"` to `requirements` in `manifest.json`

## 2. SynergridRLPStore

- [x] 2.1 Create `rlp_store.py` with `SynergridRLPStore` class skeleton (`__init__`, `async_start`, `async_stop`)
- [x] 2.2 Implement `async_start`: load from HA Storage (`krowi_energy_management_rlp_{year}`), check if today is covered
- [x] 2.3 Implement `_async_download_and_parse`: download `.xlsb` via `async_get_clientsession`, parse with `pyxlsb` in `async_add_executor_job`, return `dict[date, list[float]]`
- [x] 2.4 Implement `has_date(d: date) -> bool` and `get_weights(d: date) -> list[float] | None`
- [x] 2.5 Persist parsed data back to HA Storage after download; skip persist if loaded from cache

## 3. NordpoolBeStore — RLP buffer

- [x] 3.1 Add `rlp_store: SynergridRLPStore | None` parameter to `async_start()` in `nordpool_store.py`
- [x] 3.2 Add `_daily_rlp_buffer: dict[date, tuple[float, float]]` and load/save it from HA Storage key `krowi_energy_management_nordpool_daily_rlp_avg`
- [x] 3.3 Update `_snapshot_today()` to also write an RLP `(weighted_sum, weight_sum)` entry to `_daily_rlp_buffer` (with unweighted fallback when `rlp_store` has no weights)
- [x] 3.4 Add `monthly_average_rlp` property: `sum(ws)/sum(wt)` over `_daily_rlp_buffer` + today's live RLP contribution; `None` when `average` is `None`
- [x] 3.5 Update `_trim_buffer()` to also trim `_daily_rlp_buffer`
- [x] 3.6 Update `_async_backfill()` to also fill `_daily_rlp_buffer` for missing days

## 4. Wire up RLP store in `__init__.py`

- [x] 4.1 Instantiate `SynergridRLPStore` in `async_setup` and store in `hass.data[DOMAIN]["rlp_store"]`
- [x] 4.2 Call `await rlp_store.async_start(hass)` before `nordpool_store.async_start()`
- [x] 4.3 Pass `rlp_store` to `nordpool_store.async_start(hass, low_price_cutoff, rlp_store)`
- [x] 4.4 Call `await rlp_store.async_stop()` in `async_unload_entry` alongside `nordpool_store.async_stop()`

## 5. Electricity spot RLP sensor

- [x] 5.1 Add `UID_ELECTRICITY_SPOT_AVERAGE_PRICE_RLP = "electricity_spot_average_price_rlp"` to `const.py`
- [x] 5.2 Add EN + NL `NAMES` entries for `UID_ELECTRICITY_SPOT_AVERAGE_PRICE_RLP` to `const.py`
- [x] 5.3 Implement `ElectricitySpotAveragePriceRLPSensor` in `sensor.py` (mirrors `ElectricitySpotAveragePriceSensor` but uses `store.monthly_average_rlp` and adds `rlp_available` attribute)
- [x] 5.4 Instantiate `ElectricitySpotAveragePriceRLPSensor` in `async_setup_entry` (electricity branch) and add to entities list

## 6. Supplier constants

- [x] 6.1 Add `DOMAIN_TYPE_ELECTRICITY_SUPPLIER = "electricity_supplier"` to `const.py`
- [x] 6.2 Add `CONF_SUPPLIER_SLUG = "supplier_slug"` and `CONF_SUPPLIER_LABEL = "supplier_label"` to `const.py`
- [x] 6.3 Add `ELECTRICITY_SUPPLIER_CATALOG` dict to `const.py` with the `"mega"` entry (multipliers, offsets, flags from the spec)
- [x] 6.4 Add UID format string constants for the 4 supplier sensor patterns to `const.py`
- [x] 6.5 Add EN + NL `NAMES` entries for all 4 supplier sensor types (import price, import price EUR, export price, export price EUR) to `const.py`

## 7. Supplier config flow

- [x] 7.1 Add `"electricity_supplier"` to the `menu_options` list in `async_step_menu()`
- [x] 7.2 Implement `async_step_electricity_supplier()`: show form with `SelectSelector` (catalog keys) for slug and optional text field for label; on submit create entry with `domain_type = DOMAIN_TYPE_ELECTRICITY_SUPPLIER`
- [x] 7.3 Import new constants (`DOMAIN_TYPE_ELECTRICITY_SUPPLIER`, `CONF_SUPPLIER_SLUG`, `CONF_SUPPLIER_LABEL`, `ELECTRICITY_SUPPLIER_CATALOG`) in `config_flow.py`

## 8. Supplier sensor classes

- [x] 8.1 Implement `ElectricitySupplierImportPriceSensor` in `sensor.py`: formula `(EPEX_rlp × multiplier + offset + surcharge) × (1 + VAT/100)`, subscribes to `SIGNAL_NORDPOOL_UPDATE` + surcharge + VAT state changes
- [x] 8.2 Implement `ElectricitySupplierImportPriceEurSensor` in `sensor.py`: `import_price ÷ 100`, tracks state changes on source sensor
- [x] 8.3 Implement `ElectricitySupplierExportPriceSensor` in `sensor.py`: formula `EPEX_rlp × multiplier + offset`, no VAT, subscribes to `SIGNAL_NORDPOOL_UPDATE`
- [x] 8.4 Implement `ElectricitySupplierExportPriceEurSensor` in `sensor.py`: `export_price ÷ 100`, tracks state changes on source sensor
- [x] 8.5 Wire all 4 supplier sensor classes into `async_setup_entry` for `domain_type == DOMAIN_TYPE_ELECTRICITY_SUPPLIER`
