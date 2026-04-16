## 1. Constants (`const.py`)

- [x] 1.1 Add `CONF_ELECTRICITY_DSO = "electricity_dso"` constant
- [x] 1.2 Add `DEFAULT_ELECTRICITY_DSO = "Fluvius Zenne-Dijle"` constant
- [x] 1.3 Add `ELECTRICITY_DSO_OPTIONS: list[str]` with the 25 DSO names from the
      `RLP96UbyDGO` sheet row 1 (cols 7–31):
      `"Fluvius Antwerpen"`, `"Fluvius Limburg"`, `"Fluvius West"`,
      `"Fluvius Zenne-Dijle"`, `"Fluvius Halle-Vilvoorde"`, `"Fluvius Imewo"`,
      `"Fluvius Midden-Vlaanderen"`, `"Fluvius Kempen"`,
      `"ORES (Brabant Wallon)"`, `"ORES (Est)"`, `"ORES (Hainaut Élec2)"`,
      `"ORES (Hainaut Élec1)"`, `"ORES (Luxembourg)"`, `"ORES (Mouscron)"`,
      `"ORES (Namur)"`, `"ORES (Verviers)"`, `"RESA"`,
      `"SIBELGA-IE"`, `"SIBELGA-SE"`,
      `"Régie de Wavre"`, `"AIEG"`, `"AIESH"`,
      `"Régie de Wavre"`, `"AIEG"`, `"AIESH"`

## 2. `rlp_store.py` — URL and parser rewrite

- [x] 2.1 Replace `_RLP_URL_PATTERN` with the all-DSOs URL:
      `"https://www.synergrid.be/images/downloads/SLP-RLP-SPP/{year}/RLP0N%20{year}%20Electricity%20all%20DSOs.xlsb"`
- [x] 2.2 Add `dso_name: str` parameter to `async_start()` (after `hass`)
- [x] 2.3 Update `_async_download_and_parse()` to pass `dso_name` through to `_parse_xlsb`
- [x] 2.4 Rewrite `_parse_xlsb(data, year, dso_name)`:
      - Open sheet `"RLP96UbyDGO"` by name (not `wb.sheets[0]`)
      - Scan row 1 (index 1) from col 7 onwards to find the column index where `cell.v == dso_name`
      - If not found: log warning and return `{}`
      - Iterate data rows from index 3 onwards; skip rows where `vals[1] is None`
      - Build key as `f"{int(vals[1])}-{int(vals[2]):02d}-{int(vals[3]):02d}"`
      - Append `float(vals[dso_col])` to `result.setdefault(key, [])`
- [x] 2.5 Update the HA Storage format to wrap weights under a `"weights"` key and add a
      `"dso"` key: `{"dso": dso_name, "weights": {...}}`
- [x] 2.6 Update `_async_load()` to read the new format; if `raw.get("dso") != dso_name` or
      the format is the old flat dict (no `"dso"` key), discard and return `False`
      so that `async_start()` proceeds to re-download
- [x] 2.7 Update `_async_persist()` to save in the new format

## 3. `config_flow.py` — DSO selector in electricity options

- [x] 3.1 Import `CONF_ELECTRICITY_DSO`, `DEFAULT_ELECTRICITY_DSO`,
      `ELECTRICITY_DSO_OPTIONS` in the imports block
- [x] 3.2 Add `CONF_ELECTRICITY_DSO` field to `_electricity_options_schema()` as the first
      field (before `CONF_EXPORT_TEMPLATE`):
      ```python
      vol.Required(
          CONF_ELECTRICITY_DSO,
          default=d.get(CONF_ELECTRICITY_DSO, DEFAULT_ELECTRICITY_DSO),
      ): selector.SelectSelector(
          selector.SelectSelectorConfig(options=ELECTRICITY_DSO_OPTIONS, mode=selector.SelectSelectorMode.DROPDOWN)
      ),
      ```

## 4. `__init__.py` — pass DSO to `rlp_store.async_start()`

- [x] 4.1 Import `CONF_ELECTRICITY_DSO` and `DEFAULT_ELECTRICITY_DSO` in `__init__.py`
- [x] 4.2 In the electricity `async_setup_entry` path, read
      `dso = effective.get(CONF_ELECTRICITY_DSO, DEFAULT_ELECTRICITY_DSO)`
- [x] 4.3 Pass `dso_name=dso` to `rlp_store.async_start(hass, dso_name=dso)`
