## Context

The `ElectricitySupplierExportPriceSensor` currently uses `NordpoolBeStore.monthly_average_rlp`
as the EPEX base for the export formula. The Mega tariefkaart explicitly requires the
**SPP-weighted** average: *"het SPP-gewogen gemiddelde (gepubliceerd door synergrid)"*.

SPP (Synthetisch Productieprofiel) is Synergrid's solar PV production profile. It
concentrates weight around midday hours when solar generation peaks and day-ahead prices
tend to be lower. Using RLP (consumption-weighted) instead overestimates the export price
because RLP has more weight on morning/evening when prices are higher.

The SPP file for 2026 has been inspected and is fully understood:
- URL: `https://www.synergrid.be/images/downloads/SLP-RLP-SPP/{year}/SPP_ex-ante_and_ex-post_{year}.xlsx`
- Sheet: `SPP_ex-ante_2026` (rId3 → `sheet3.xml`)
- Columns: `[UTC_serial, Year, Month, Day, Hour, Min, SPPExanteBE]`
- Rows: 35040 = 365 days × 96 QH slots (exactly; DST days skip H=2, still 96 rows)
- Format: `.xlsx` (ZIP of XML) — parseable with stdlib `zipfile` + `xml.etree.ElementTree`, no new dependency
- No per-DSO column: single `SPPExanteBE` column for all of Belgium (since 2025)
- Ex-post data only covers 2020S2–2025S1; no 2026 ex-post exists. Ex-ante is the only option.

The existing `SynergridRLPStore` / `NordpoolBeStore` RLP integration is the direct
structural template for this change. SPP follows the same download-parse-cache-buffer-property
pattern.

## Goals / Non-Goals

**Goals:**
- Add `SynergridSPPStore` that downloads, parses and caches the annual SPP ex-ante profile
- Add `NordpoolBeStore.monthly_average_spp` property (SPP-weighted rolling average)
- Switch `ElectricitySupplierExportPriceSensor` to use `monthly_average_spp`
- No new manifest requirement — use stdlib parser

**Non-Goals:**
- Ex-post SPP weighting (no 2026 data exists; ex-ante is correct for live estimation)
- Per-DSO SPP selection (file is Belgium-wide since 2025)
- Any import sensor changes
- Config flow changes
- Year rollover handling beyond what RLP already does

## Decisions

### D1 — Standalone `SynergridSPPStore` (mirrors `SynergridRLPStore`)

**Chosen**: New `spp_store.py` with `SynergridSPPStore` class, structurally parallel to
`SynergridRLPStore`. `NordpoolBeStore` accepts an optional `spp_store` parameter alongside
the existing `rlp_store`.

**Alternative rejected**: Generalise into a single `SynergridProfileStore` with a `mode`
parameter. Rejected because:
1. RLP uses `pyxlsb` (binary xlsx); SPP uses stdlib XML — different parsers
2. RLP requires DSO column selection; SPP does not — forcing a shared interface adds
   unnecessary complexity with no real code reuse on the hot path

**Alternative rejected**: Inline SPP download inside `NordpoolBeStore`. Rejected because it
mixes concerns and makes `nordpool_store.py` harder to test in isolation.

### D2 — Stdlib XML parser, no new dependency

**Chosen**: Parse `.xlsx` as a ZIP, extract `xl/worksheets/sheet3.xml` with
`xml.etree.ElementTree`, read `x:v` elements from `x:c` cells. Confirmed working in the
inspection spike — the data cells are all numeric (no shared string lookups needed for the
weight column).

**Alternative rejected**: `openpyxl`. Not in the HA venv or manifest. Adding it would be
a new `requirements` entry for a single-file use case that stdlib already handles.

### D3 — Sheet identified by name lookup, not hardcoded index

**Chosen**: Parse `xl/workbook.xml` to find the `rId` for `SPP_ex-ante_{year}`, then resolve
to the sheet file via `xl/_rels/workbook.xml.rels`. This is robust to sheet order changes in
future file revisions.

**Alternative rejected**: Hardcode `sheet3.xml`. Fragile if Synergrid reorders sheets.

### D4 — SPP buffer in `NordpoolBeStore` mirrors RLP buffer exactly

`_daily_spp_buffer: dict[date, tuple[float, float]]` — same `(weighted_sum, weight_total)`
tuple format as `_daily_rlp_buffer`. `_snapshot_today()`, `_trim_buffer()`, and
`_async_backfill()` each gain parallel SPP operations. `monthly_average_spp` property mirrors
`monthly_average_rlp`.

Storage key: `krowi_energy_management_nordpool_daily_spp_avg` (new HA Storage entry).

### D5 — Graceful fallback to `monthly_average_rlp` if SPP unavailable

If `SynergridSPPStore` fails to download (network error, file format change), export sensors
fall back to `monthly_average_rlp` with a warning log. This preserves existing behaviour
rather than making export sensors unavailable.

**Trade-off**: Fallback silently degrades accuracy. Acceptable for a live estimation sensor.

## Risks / Trade-offs

- **Synergrid changes sheet structure** → Mitigated by D3 (name-based sheet lookup) and the
  fact that this file format has been stable across years 2020–2026.
- **52 MB download on each year change** → Same situation as RLP. Persisted to HA Storage
  immediately after parsing; only re-downloaded when the new year's entry is missing.
- **DST days have 96 rows but skip H=2** → Inspection confirmed the file always has exactly
  96 rows per calendar day. Alignment with Nord Pool slots is by row index within the day,
  not by timestamp matching — consistent with how RLP weights are applied.
- **No 2027 file until ~Jan 2027** → Year rollover: if the new year's file isn't available
  yet, SPP store stays on prior year's data. RLP has the same behaviour.
