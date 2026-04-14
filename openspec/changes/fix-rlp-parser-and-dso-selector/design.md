## Context

`SynergridRLPStore` exists and is wired into `NordpoolBeStore`, but its parser has two bugs:

1. **Wrong sheet**: `wb.sheets[0]` resolves to `"Description"` — a metadata tab with no
   weights. The parser finds no dates and returns `{}` silently. Every call to
   `get_weights()` returns `None` and `NordpoolBeStore` falls back to the unweighted
   average.

2. **Wrong file**: The single-DSO URL (`RLP0N {year} Electricity.xlsb`) contains weights
   for the Walloon AIESH model. Flemish users (Fluvius) get ~4% wrong weights; Brussels
   users (SIBELGA) get ~38% wrong weights. The correct file is
   `RLP0N {year} Electricity all DSOs.xlsb` which has one column per DSO (confirmed by
   live inspection of the 2026 file).

The `all DSOs` file structure (confirmed):
```
Sheet: "RLP96UbyDGO"
Row 0: RLP model names (col 6 = "RLP", col 7+ = internal model names)
Row 1: DGO names      (col 6 = "DGO", col 7+ = human-readable DSO names)
Row 2: EAN codes      (header row with EAN identifiers)
Row 3+: data rows     (col 1=Year, col 2=Month, col 3=Day, col 4=h, col 5=Min,
                       col 6=Date serial, col 7+ = RLPestU weight per DSO)
96 rows per calendar day (one per 15-min QH slot, chronological).
```

DSOs in the 2026 file (cols 7–31):
- Fluvius Antwerpen, Fluvius Limburg, Fluvius West, Fluvius Zenne-Dijle,
  Fluvius Halle-Vilvoorde, Fluvius Imewo, Fluvius Midden-Vlaanderen, Fluvius Kempen,
  ORES (Brabant Wallon), ORES (Est), ORES (Hainaut Élec2), ORES (Hainaut Élec1),
  ORES (Luxembourg), ORES (Mouscron), ORES (Namur), ORES (Verviers), RESA,
  SIBELGA-IE, SIBELGA-SE, Régie de Wavre, AIEG, AIESH, Régie de Wavre, AIEG, AIESH

All 8 Fluvius DSOs share identical weight values for 2026.

## Goals / Non-Goals

**Goals:**
- Fix the parser to read `RLP96UbyDGO` sheet from `all DSOs` file
- Make the DSO configurable via the electricity options flow
- Default DSO is `"Fluvius Zenne-Dijle"`

**Non-Goals:**
- Changing the `NordpoolBeStore` buffers or the `monthly_average_rlp` property
- Adding SPP weighting (separate change)
- Changing any sensors or entity IDs

## Decisions

### D1 — Use `RLP0N {year} Electricity all DSOs.xlsb` with DSO column selection

The `all DSOs` file is the authoritative source for per-DSO weights and has a clean, stable
URL pattern (`SLP-RLP-SPP/{year}/RLP0N%20{year}%20Electricity%20all%20DSOs.xlsb`).
The parser reads DSO names from row 1, finds the column index matching `dso_name`, and
extracts weights from that column only.

Alternative: Keep single-file URL, fix the sheet name — rejected because the single file
contains the wrong weights for Flemish users.

### D2 — DSO name stored in the electricity config entry options

`CONF_ELECTRICITY_DSO` is added to the electricity options flow as a `SelectSelector`,
mirroring `CONF_GOS_ZONE` in the gas flow. The effective value is read in `__init__.py`
via the usual `effective = {**entry.data, **entry.options}` pattern.

Default is `"Fluvius Zenne-Dijle"` (`DEFAULT_ELECTRICITY_DSO`).

Existing installations that have no `CONF_ELECTRICITY_DSO` key will automatically use
the default on their next restart — no migration needed.

### D3 — Parser signature: `_parse_xlsb(data, year, dso_name)` 

The DSO name is passed into the parser at call time. `async_start()` gains a `dso_name: str`
parameter. This keeps the store's API explicit and avoids storing the DSO name as instance
state (it is only needed during parsing).

### D4 — Invalidation: re-download when DSO changes

If the user changes their DSO in the options flow, the cached storage may contain weights
for the old DSO. The simplest fix: `async_start()` compares the stored DSO name against the
configured one; if they differ, it discards the cache and re-downloads.

The HA Storage payload gains a `"dso"` top-level key alongside the day weights.

### D5 — `ELECTRICITY_DSO_OPTIONS` hardcoded from the 2026 file inspection

The list of valid DSO names is stable year-to-year (same Belgian grid operators). It is
hardcoded as `ELECTRICITY_DSO_OPTIONS` in `const.py` rather than downloaded at config
time. If Synergrid restructures the file, the constant can be updated in the next release.

## Parser Logic (new)

```python
def _parse_xlsb(data: bytes, year: int, dso_name: str) -> dict[str, list[float]]:
    with pyxlsb.open_workbook(io.BytesIO(data)) as wb:
        with wb.get_sheet("RLP96UbyDGO") as sheet:
            rows = list(sheet.rows())

    # Row 1 (index 1): DGO names starting at col 7
    dgo_header = rows[1]
    dso_col = None
    for col_idx, cell in enumerate(dgo_header):
        if cell and cell.v == dso_name:
            dso_col = col_idx
            break

    if dso_col is None:
        # warn and return empty
        return {}

    # Row 3+ (index 3+): data rows
    result: dict[str, list[float]] = {}
    for row in rows[3:]:
        vals = [c.v if c else None for c in row]
        if vals[1] is None:
            continue
        key = f"{int(vals[1])}-{int(vals[2]):02d}-{int(vals[3]):02d}"
        w = vals[dso_col]
        if w is not None:
            result.setdefault(key, []).append(float(w))

    return result
```

## Storage Schema Change

Old storage format (key `krowi_energy_management_rlp_{year}`):
```json
{ "2026-01-01": [0.0000442, ...], ... }
```

New storage format:
```json
{ "dso": "Fluvius Zenne-Dijle", "weights": { "2026-01-01": [0.0000460, ...], ... } }
```

The load path checks `raw.get("dso") == dso_name`; on mismatch or on the old flat format,
it discards the cache and re-downloads.
