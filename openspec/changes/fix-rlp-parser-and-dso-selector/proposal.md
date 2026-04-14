## Why

The `SynergridRLPStore` parser in `rlp_store.py` has been silently broken since it was
introduced. It reads `wb.sheets[0]` which resolves to the `Description` sheet — a metadata
sheet with no data. As a result, the parser finds no dates, returns an empty dictionary, and
`NordpoolBeStore` falls back to the unweighted average for every day.
`electricity_spot_average_price_rlp` has therefore never produced an RLP-weighted value: it
has always equalled `electricity_spot_average_price` (unweighted).

A second issue is that the parser was pointed at the single-DSO file
(`RLP0N {year} Electricity.xlsb`) which actually contains Walloon weights (AIESH/Walloon
model). A Flemish user (Fluvius) should use Fluvius-specific weights, which differ by ~4%
on Jan 1 and diverge further on seasonal days. The correct source is the
`RLP0N {year} Electricity all DSOs.xlsb` file, which contains a column per DSO and allows
exact matching.

This change fixes both issues: rewrite the parser to read the correct sheet from the correct
file, and add a DSO selector to the electricity config entry so users get weights for their
own network operator.

## What Changes

- **Fix `rlp_store.py`**: switch to the `all DSOs` URL, add a `dso_name` parameter to
  `async_start()`, rewrite `_parse_xlsb` to target the `RLP96UbyDGO` sheet and extract
  weights from the column matching the configured DSO.
- **Add `CONF_ELECTRICITY_DSO` and `ELECTRICITY_DSO_OPTIONS`** to `const.py` — the complete
  list of 25 DSOs from the Synergrid file; default `"Fluvius Zenne-Dijle"`.
- **Add DSO selector** to the electricity config entry options flow (mirrors
  `CONF_GOS_ZONE` in the gas flow).
- **Wire the DSO** through `__init__.py` when calling `rlp_store.async_start()`.

## Capabilities

### Modified Capabilities

- `synergrid-rlp-store`: Parser rewritten; now downloads the all-DSOs file, finds the
  correct DSO column, and produces genuinely RLP-weighted per-slot weights. DSO is
  configurable; default is Fluvius Zenne-Dijle.
- `electricity-tariff-entities`: Electricity config entry gains a `CONF_ELECTRICITY_DSO`
  field (options flow), following the same pattern as `CONF_GOS_ZONE` for gas.

## Impact

- `rlp_store.py`: URL constant updated; `async_start()` signature gains `dso_name: str`;
  `_parse_xlsb` rewritten for the new sheet/column structure.
- `const.py`: Add `CONF_ELECTRICITY_DSO`, `DEFAULT_ELECTRICITY_DSO`,
  `ELECTRICITY_DSO_OPTIONS`.
- `config_flow.py`: Add `CONF_ELECTRICITY_DSO` `SelectSelector` to the electricity options
  step.
- `__init__.py`: Read `CONF_ELECTRICITY_DSO` from the effective config and pass to
  `rlp_store.async_start()`.
