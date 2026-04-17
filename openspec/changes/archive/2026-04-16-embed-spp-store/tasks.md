## 1. SynergridSPPStore (new file)

- [x] 1.1 Create `spp_store.py` with `SynergridSPPStore` class skeleton (mirroring `rlp_store.py` structure): `__init__`, `available` property, `async_start()`, `async_stop()`, `get_weights(d)`
- [x] 1.2 Implement stdlib XML parser: open xlsx as zip, locate `SPP_ex-ante_{year}` sheet via `xl/workbook.xml` + `xl/_rels/workbook.xml.rels`, parse `xl/worksheets/sheetN.xml` extracting `SPPExanteBE` column (col index 6) into `dict[str, list[float]]`
- [x] 1.3 Implement `_async_load(year)`: load from HA Storage key `krowi_energy_management_spp_{year}`, validate format, return `True` if today's date is present
- [x] 1.4 Implement `_async_download_and_parse(year)`: fetch URL, delegate parsing to executor job, persist result to HA Storage, set `_available`
- [x] 1.5 Implement `async_start()`: derive year, check cache, download if needed, set `_available`
- [x] 1.6 Verify: `get_weights(date.today())` returns 96 floats with night slots = 0.0 and midday slots > 0

## 2. NordpoolBeStore — SPP buffer and property

- [x] 2.1 Add `_spp_store: SynergridSPPStore | None` and `_daily_spp_buffer: dict[date, tuple[float, float]]` fields to `NordpoolBeStore.__init__()`
- [x] 2.2 Add `spp_store` parameter to `async_start()`; wire `self._spp_store = spp_store`
- [x] 2.3 Add `_async_load_spp_buffer()` and `_save_spp_buffer()` (storage key: `krowi_energy_management_nordpool_daily_spp_avg`); call load in `async_start()`
- [x] 2.4 Implement `_compute_spp_entry(d, slots)` — mirrors `_compute_rlp_entry()` but uses `self._spp_store.get_weights(d)`
- [x] 2.5 Extend `_snapshot_today()` to also compute and store the SPP entry for yesterday into `_daily_spp_buffer` and persist
- [x] 2.6 Extend `_trim_buffer()` to also trim `_daily_spp_buffer`
- [x] 2.7 Extend `_async_backfill()` to also populate `_daily_spp_buffer` for missing dates
- [x] 2.8 Add `monthly_average_spp` property — same weighted-sum/weight-total formula as `monthly_average_rlp` but using `_daily_spp_buffer` and `_compute_spp_entry()`

## 3. Export sensor — switch to SPP average

- [x] 3.1 In `ElectricitySupplierExportPriceSensor._update()`: replace `store.monthly_average_rlp` with `store.monthly_average_spp`
- [x] 3.2 Update unavailability guard: sensor is unavailable when `store.monthly_average_spp is None`

## 4. Wiring in `__init__.py`

- [x] 4.1 Import `SynergridSPPStore` in `__init__.py`
- [x] 4.2 Instantiate `SynergridSPPStore` alongside `SynergridRLPStore` in the electricity entry setup
- [x] 4.3 Pass `spp_store` to `NordpoolBeStore.async_start()`
- [x] 4.4 Call `spp_store.async_stop()` in the integration unload handler

## 5. Documentation

- [x] 5.1 Update `docs/suppliers/mega.md` — remove the "current implementation gap" note from the export section now that SPP is implemented
- [x] 5.2 Bump `manifest.json` version (`0.0.x` increment)
