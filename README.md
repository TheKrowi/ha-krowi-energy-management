# Krowi Energy Management

A Home Assistant custom integration that fetches Belgian day-ahead electricity and gas spot prices, applies tariff surcharges and VAT, and accumulates monetary cost using your P1 meter data. Designed for Belgian residential connections (Fluvius, ORES, SIBELGA DSOs).

---

## Prerequisites

- Home Assistant with HACS installed
- A Belgian electricity connection served by one of the supported DSOs (Fluvius, ORES, RESA, SIBELGA, …)
- A P1 digital meter connected to HA (provides `sensor.*_energy_import/export_tariff_*` entities)
- A gas meter sensor in HA reporting cumulative consumption in m³ (`state_class: total_increasing`)

---

## Installation

1. Open HACS → **Integrations** → three-dot menu → **Custom repositories**
2. Add `https://github.com/TheKrowi/ha-krowi-energy-management` as **Integration**
3. Install **Krowi Energy Management**
4. Restart Home Assistant
5. Go to **Settings → Devices & Services → Add Integration → Krowi Energy Management**

---

## Configuration

The integration uses **multiple config entries**, one per domain. The setup menu offers four entry types:

| Entry type | `domain_type` | Limit | Purpose |
|---|---|---|---|
| Electricity | `electricity` | 1 | Fetches EPEX SPOT BE prices, creates tariff inputs and price/cost sensors |
| Gas | `gas` | 1 | Fetches TTF DAM and GCV data, creates tariff inputs and price/cost sensors |
| Settings | `settings` | 1 | Global language preference (EN / NL) |
| Electricity Supplier | `electricity_supplier` | Multiple | Supplier-formula price sensors (e.g. Mega) |

### Electricity options

| Option | Default | Description |
|---|---|---|
| DSO | `Fluvius Zenne-Dijle` | Your Belgian electricity distribution operator |
| Export price template | (Jinja2 formula) | Template evaluated to produce the export price in c€/kWh |
| Low price cutoff | `1.0` | Threshold (c€/kWh) below which `low_price` attribute is `true` |
| Import T1/T2 meter entity | `sensor.energy_meter_energy_import_tariff_*` | P1 meter entities for cost accumulation |
| Export T1/T2 meter entity | `sensor.energy_meter_energy_export_tariff_*` | P1 meter entities for revenue accumulation |
| Import T1/T2 price entity | `sensor.electricity_current_price_import_eur` | EUR/kWh price used for cost calculation |
| Export T1/T2 price entity | `sensor.electricity_current_price_export_eur` | EUR/kWh price used for revenue calculation |

### Gas options

| Option | Default | Description |
|---|---|---|
| GOS zone | `GOS FLUVIUS - LEUVEN` | Belgian gas offtake station zone (from Mijn Fluvius → Technische gegevens) |
| Gas meter entity | `sensor.gas_meter_consumption` | Entity reporting cumulative gas consumption in m³ |

---

## Entities

### Electricity — number (input) entities

All values persist across restarts via `RestoreNumber`. Input mode is text box.

| Entity ID | Friendly name (NL) | Unit | Range | Step |
|---|---|---|---|---|
| `number.electricity_tariff_green_energy_contribution` | Groene stroom bijdrage | c€/kWh | 0–9999 | 0.00001 |
| `number.electricity_tariff_distribution_transport` | Distributie & transport | c€/kWh | 0–9999 | 0.00001 |
| `number.electricity_tariff_excise_duty` | Bijzondere accijns | c€/kWh | 0–9999 | 0.00001 |
| `number.electricity_tariff_energy_contribution` | Energiebijdrage | c€/kWh | 0–9999 | 0.00001 |
| `number.electricity_vat` | BTW | % | 0–100 | 0.01 |

### Electricity — sensor entities

| Entity ID | Friendly name (NL) | Unit | Description |
|---|---|---|---|
| `sensor.electricity_spot_current_price` | Huidige prijs (EPEX SPOT) | c€/kWh | Active 15-min EPEX SPOT BE slot price. Attributes: `today`, `tomorrow`, `tomorrow_valid`, `low_price`, `price_percent_to_average`. |
| `sensor.electricity_spot_average_price` | Gemiddelde maandprijs (EPEX SPOT) | c€/kWh | Rolling calendar-month unweighted average. Attribute `history` contains the completed-day buffer (`YYYY-MM-DD → float`). |
| `sensor.electricity_spot_average_price_rlp` | RLP-gewogen maandgemiddelde (EPEX SPOT) | c€/kWh | Rolling calendar-month average **weighted by the Synergrid RLP0N consumption profile** (DSO-specific). Used by supplier import price formulas. Unavailable for ~30 days on first install while buffer fills. |
| `sensor.electricity_spot_average_price_spp` | SPP-gewogen maandgemiddelde (EPEX SPOT) | c€/kWh | Rolling calendar-month average **weighted by the Synergrid SPP ex-ante solar production profile**. Used by supplier export price formulas. |
| `sensor.electricity_tariff_total_surcharge` | Totale toeslag | c€/kWh | Sum of the four tariff rate number entities (excl. VAT). Rounded to 5 dp. |
| `sensor.electricity_tariff_total_surcharge_formula` | Totale toeslag formule | — | Human-readable formula string, e.g. `0.01250 + 0.03750 + 0.00422 + 0.00020 = 0.05442 c€/kWh`. |
| `sensor.electricity_current_price_import` | Actuele importprijs | c€/kWh | `(spot_current + surcharge) × (1 + vat/100)`. Unavailable when spot price is unavailable. |
| `sensor.electricity_current_price_export` | Actuele exportprijs | c€/kWh | Rendered from the user-supplied Jinja2 export template. Tracks all referenced entities reactively. |
| `sensor.electricity_current_price_import_eur` | Actuele importprijs (EUR/kWh) | EUR/kWh | `import_price ÷ 100`. For use with the HA Energy Dashboard. |
| `sensor.electricity_current_price_export_eur` | Actuele exportprijs (EUR/kWh) | EUR/kWh | `export_price ÷ 100`. For use with the HA Energy Dashboard. |
| `sensor.electricity_import_cost_tariff_1` | Importkosten (tarief 1) | EUR | Accumulated import cost for tariff 1. `state_class: total_increasing`. Persisted via `RestoreEntity`. |
| `sensor.electricity_import_cost_tariff_2` | Importkosten (tarief 2) | EUR | Accumulated import cost for tariff 2. Same mechanics as T1. |
| `sensor.electricity_export_revenue_tariff_1` | Exportopbrengst (tarief 1) | EUR | Accumulated export revenue for tariff 1. |
| `sensor.electricity_export_revenue_tariff_2` | Exportopbrengst (tarief 2) | EUR | Accumulated export revenue for tariff 2. |
| `sensor.electricity_total_import_cost` | Totale importkosten | EUR | `import_T1 + import_T2`. Derived, not accumulated directly. |
| `sensor.electricity_total_export_revenue` | Totale exportopbrengst | EUR | `export_T1 + export_T2`. |
| `sensor.electricity_net_cost` | Netto elektriciteitskosten | EUR | `total_import_cost − total_export_revenue`. |

#### Cost accumulator mechanics

The four per-tariff sensors (`import_cost_tariff_1/2`, `export_revenue_tariff_1/2`) track their meter entity and multiply the delta in kWh by the configured EUR/kWh price entity on every meter state change:

- **First reading after startup**: anchored, no cost added (restart gap is not costed).
- **Positive delta**: `total += Δkwh × price_EUR/kWh`.
- **Negative delta** (meter replaced): re-anchors silently, total unchanged.
- **Price unavailable at tick time**: falls back to last known valid price; skips tick if no prior price seen.
- **Value survives restarts** via `RestoreEntity`.

---

### Gas — number (input) entities

| Entity ID | Friendly name (NL) | Unit | Range | Step |
|---|---|---|---|---|
| `number.gas_tariff_distribution` | Distributie | c€/kWh | 0–9999 | 0.00001 |
| `number.gas_tariff_transport` | Transport (Fluxys) | c€/kWh | 0–9999 | 0.00001 |
| `number.gas_tariff_excise_duty` | Bijzondere accijns | c€/kWh | 0–9999 | 0.00001 |
| `number.gas_tariff_energy_contribution` | Energiebijdrage | c€/kWh | 0–9999 | 0.00001 |
| `number.gas_vat` | BTW | % | 0–100 | 0.01 |

### Gas — sensor entities

| Entity ID | Friendly name (NL) | Unit | Description |
|---|---|---|---|
| `sensor.gas_spot_today_price` | Dagprijs (TTF DAM) | c€/kWh | Latest daily TTF DAM price from the Elindus API. Unavailable until first successful fetch. |
| `sensor.gas_spot_average_price` | Gemiddelde maandprijs (TTF DAM) | c€/kWh | Rolling calendar-month average TTF DAM price. |
| `sensor.gas_tariff_total_surcharge` | Totale toeslag | c€/kWh | Sum of the four gas tariff rate entities. |
| `sensor.gas_tariff_total_surcharge_formula` | Totale toeslag formule | — | Human-readable formula string. |
| `sensor.gas_current_price` | Actuele prijs | c€/kWh | `(spot_average + surcharge) × (1 + vat/100)`. Based on the 30-day rolling TTF average (not today's spot). |
| `sensor.gas_current_price_eur` | Actuele prijs (EUR/kWh) | EUR/kWh | `gas_current_price ÷ 100`. For use with the HA Energy Dashboard. |
| `sensor.gas_calorific_value` | Calorische waarde | kWh/m³ | Monthly GCV for the configured GOS zone from Atrias. Attributes: `history` (`YYYY-MM → float`, 12 months), `data_is_fresh`. |
| `sensor.gas_current_price_m3` | Actuele prijs (m³) | €/m³ | `gas_current_price_eur × calorific_value`. |
| `sensor.gas_consumption_kwh` | Gasverbruik | kWh | `gas_meter_m3 × calorific_value`. `state_class: total_increasing`, `device_class: energy`. For the HA Energy Dashboard. |
| `sensor.gas_total_cost` | Totale gaskosten | EUR | Accumulated `Σ(Δm³ × GCV × price_EUR/kWh)`. `state_class: total_increasing`. Persisted via `RestoreEntity`. Same restart/fallback mechanics as electricity cost sensors. |

---

### Electricity supplier — sensor entities

Each electricity supplier config entry creates 4 sensors using the slug as an infix. For Mega (`slug = "mega"`):

| Entity ID | Unit | VAT | Description |
|---|---|---|---|
| `sensor.electricity_mega_import_price` | c€/kWh | yes | `(EPEX_RLP × 1.061 + surcharge) × (1 + vat/100)` |
| `sensor.electricity_mega_import_price_eur` | EUR/kWh | yes | `import_price ÷ 100` |
| `sensor.electricity_mega_export_price` | c€/kWh | exempt | `EPEX_SPP × 0.94 − 1.7` |
| `sensor.electricity_mega_export_price_eur` | EUR/kWh | exempt | `export_price ÷ 100` |

Both supplier sensors depend on the RLP/SPP-weighted monthly averages and are unavailable until those buffers are populated (~30 days on first install).

Adding additional suppliers requires extending `ELECTRICITY_SUPPLIER_CATALOG` in `const.py`. See [`docs/supplier-formulas.md`](docs/supplier-formulas.md) for the catalog schema.

---

## Data Stores

The integration embeds five internal data stores. No external integrations are required.

### NordpoolBeStore

**Source:** `https://dataportal-api.nordpoolgroup.com/api/DayAheadPrices`  
**Delivers data to:** all `electricity_spot_*` sensors

Fetches 15-minute EPEX SPOT Belgium day-ahead price slots in EUR. Values are converted to c€/kWh at ingest by dividing by 10.

**Fetch schedule:**

| Trigger | Action |
|---|---|
| Startup | Load buffer from HA Storage; fetch today; backfill any missing calendar-month days; fetch tomorrow if ≥ 13:00 |
| `00:00:01` daily | Snapshot yesterday's average to buffer; re-fetch today; clear tomorrow cache |
| `13:01:00` daily | Fetch tomorrow's prices if not yet available |
| Every `X:00:01`, `X:15:01`, `X:30:01`, `X:45:01` | Update `current_price` from cached today-slots; retry tomorrow if not valid; dispatch `SIGNAL_NORDPOOL_UPDATE` |

**Persistence:** Three HA Storage entries hold rolling calendar-month daily averages (unweighted, RLP-weighted, SPP-weighted). Backfill runs at startup to fill any gaps. Old entries (> 1 calendar month) are pruned on every write.

---

### SynergridRLPStore

**Source:** `https://www.synergrid.be/images/downloads/SLP-RLP-SPP/{year}/RLP0N%20{year}%20Electricity%20all%20DSOs.xlsb`  
**Delivers data to:** `electricity_spot_average_price_rlp`, supplier import price sensors

Downloads and parses the annual Synergrid RLP0N residential consumption profile for the configured DSO. Provides 96 quarter-hour weight values per calendar day.

**Fetch schedule:**

| Trigger | Action |
|---|---|
| Startup | Load from HA Storage cache for the current year; download if today's date is absent from cache |
| `00:00:01` on 1 January | Swap to new year's storage key; load from cache or download |
| `00:00:01`, 26–31 December | Attempt to pre-fetch next year's profile; send HA notification on success or failure |

**Persistence:** Cached in HA Storage under `krowi_energy_management_rlp_{year}`. Cache is invalidated if the configured DSO name changes.

**Dependency:** `pyxlsb>=1.0.10` (declared in `manifest.json`).

---

### SynergridSPPStore

**Source:** `https://www.synergrid.be/images/downloads/SLP-RLP-SPP/{year}/SPP_ex-ante_and_ex-post_{year}.xlsx`  
**Delivers data to:** `electricity_spot_average_price_spp`, supplier export price sensors

Downloads and parses the annual Synergrid SPP ex-ante solar production profile. Provides 96 quarter-hour weight values per calendar day (zero at night, peak at noon).

**Fetch schedule:** Same triggers as RLPStore — startup cache load/download, Jan 1 year rollover, and Dec 26–31 pre-fetch with HA notifications. Cached under `krowi_energy_management_spp_{year}`. Parsed using stdlib (`zipfile` + `xml.etree.ElementTree`), no extra dependency.

---

### TtfDamStore

**Source:** `https://mijn.elindus.be/marketinfo/dayahead/prices?market=GAS&granularity=DAY`  
**Delivers data to:** `gas_spot_today_price`, `gas_spot_average_price`

Fetches a rolling calendar-month window (`from = today − 1 month`, `to = today`) of daily TTF DAM prices. Converts EUR/MWh → c€/kWh by dividing by 10. Compares the date of the last data point to today to determine `data_is_fresh`.

**Fetch schedule:**

| Trigger | Action |
|---|---|
| Startup | Immediate fetch |
| `00:00:01` daily | Reset `data_is_fresh = False`; re-fetch |
| Every `X:00:01` and `X:30:01` | Fetch if `data_is_fresh = False` (retry until today's data appears) |

**Persistence:** None. Data is always re-fetched from the Elindus API.

---

### GcvStore

**Source:** `https://api.atrias.be/roots/download/SectorData%2F02%20Gross%20Calorific%20Values%2F{YEAR}%2FGCV{YEAR}{MM}.txt?subscription-key=…`  
**Delivers data to:** `gas_calorific_value`, `gas_current_price_m3`, `gas_consumption_kwh`, `gas_total_cost`

Fetches the monthly GCV CSV file for the configured GOS zone from the Atrias API. The target is always the **prior calendar month** — Atrias publishes month M's data in early month M+1.

**Fetch schedule:**

| Trigger | Action |
|---|---|
| Startup | Load 12-month history from HA Storage; fetch any missing months (oldest first) |
| `00:00:01` on the 1st of each month | Reset `data_is_fresh = False`; trigger refresh |
| `06:00:01` daily | Fetch if `data_is_fresh = False` |
| 60 s after startup (if `gcv = None`) | Startup retry |

**Persistence:** 12-month rolling history (`YYYY-MM → float`) in HA Storage under `krowi_energy_management_gcv_history`. A 404 from the API (file not yet published) is silently skipped and retried next day.

---

## Diagnostic Actions

Three HA actions (services) are registered when the **Gas** config entry is active. They are callable from **Developer Tools → Actions** and return a response payload — useful for troubleshooting GCV fetch issues without digging into logs.

### `krowi_energy_management.gcv_test_connection`

Performs a plain TLS handshake against `api.atrias.be:443` and reports whether SSL verification succeeds.

**Parameters:** none

**Response:**

| Field | Type | Description |
|---|---|---|
| `ok` | `bool` | `true` if the handshake completed without errors |
| `error` | `string \| null` | Error message if `ok` is `false`, otherwise `null` |

**Example response (success):**
```json
{ "ok": true, "error": null }
```

---

### `krowi_energy_management.gcv_test_fetch`

Performs a live HTTP fetch of the GCV file for the specified month and parses it for the configured GOS zone. Does **not** modify the store state or history.

**Parameters (all optional):**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `year` | `int` | prior month | Year to fetch (2020–2040) |
| `month` | `int` | prior month | Month to fetch (1–12) |

**Response:**

| Field | Type | Description |
|---|---|---|
| `ok` | `bool` | `true` if a GCV value was successfully parsed |
| `target_month` | `string` | `"YYYY-MM"` of the fetched file |
| `zone` | `string` | Configured GOS zone |
| `http_status` | `int \| null` | HTTP status code returned by the API |
| `gcv_value` | `float \| null` | Parsed GCV in kWh/m³, or `null` on failure |
| `error` | `string \| null` | Error description, or `null` on success |

**Example response (success):**
```json
{
  "ok": true,
  "target_month": "2026-04",
  "zone": "GOS FLUVIUS - LEUVEN",
  "http_status": 200,
  "gcv_value": 10.8732,
  "error": null
}
```

**Example response (file not yet published):**
```json
{
  "ok": false,
  "target_month": "2026-05",
  "zone": "GOS FLUVIUS - LEUVEN",
  "http_status": 404,
  "gcv_value": null,
  "error": "404 Not Found — file not yet published by Atrias"
}
```

---

### `krowi_energy_management.gcv_store_state`

Returns a snapshot of the current in-memory GCV store state without making any network calls.

**Parameters:** none

**Response:**

| Field | Type | Description |
|---|---|---|
| `zone` | `string` | Configured GOS zone |
| `gcv` | `float \| null` | Current GCV value in kWh/m³ (`null` if no data yet) |
| `data_is_fresh` | `bool` | `true` when the most recent prior-month file has been fetched |
| `target_month` | `string` | `"YYYY-MM"` of the month currently being targeted |
| `history_count` | `int` | Number of months in history (max 12) |
| `history` | `object` | Full rolling history as `{ "YYYY-MM": float }`, sorted chronologically |

**Example response:**
```json
{
  "zone": "GOS FLUVIUS - LEUVEN",
  "gcv": 10.8732,
  "data_is_fresh": true,
  "target_month": "2026-04",
  "history_count": 12,
  "history": {
    "2025-05": 10.6210,
    "2025-06": 10.5890,
    "...": "...",
    "2026-04": 10.8732
  }
}
```

---

### `krowi_energy_management.rlp_store_state`

Returns a snapshot of the current in-memory RLP store state without making any network calls.

**Parameters:** none

**Response:**

| Field | Type | Description |
|---|---|---|
| `available` | `bool` | `true` if weights are loaded and the store is operational |
| `loaded_year` | `int` | Year the currently loaded profile covers |
| `dso` | `string` | Configured DSO name |
| `date_count` | `int` | Number of dates with weight data |
| `has_today` | `bool` | `true` if today's date is present in the weights |
| `first_date` | `string \| null` | First date in the profile (`YYYY-MM-DD`) |
| `last_date` | `string \| null` | Last date in the profile (`YYYY-MM-DD`) |

---

### `krowi_energy_management.spp_store_state`

Returns a snapshot of the current in-memory SPP store state without making any network calls.

**Parameters:** none

**Response:**

| Field | Type | Description |
|---|---|---|
| `available` | `bool` | `true` if weights are loaded and the store is operational |
| `loaded_year` | `int` | Year the currently loaded profile covers |
| `date_count` | `int` | Number of dates with weight data |
| `has_today` | `bool` | `true` if today's date is present in the weights |
| `first_date` | `string \| null` | First date in the profile (`YYYY-MM-DD`) |
| `last_date` | `string \| null` | Last date in the profile (`YYYY-MM-DD`) |

---

### `krowi_energy_management.rlp_test_fetch`

Performs a live download and parse of the RLP profile for the specified year. Does **not** modify the store state.

**Parameters (optional):**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `year` | `int` | current year | Year to fetch (2020–2040) |

**Response:**

| Field | Type | Description |
|---|---|---|
| `ok` | `bool` | `true` if the profile was successfully downloaded and parsed |
| `year` | `int` | Year that was fetched |
| `dso` | `string` | Configured DSO name |
| `http_status` | `int \| null` | HTTP status code from the download |
| `date_count` | `int \| null` | Number of dates parsed, or `null` on failure |
| `has_today` | `bool \| null` | `true` if today's date is in the parsed data |
| `first_date` | `string \| null` | First date in the parsed profile |
| `last_date` | `string \| null` | Last date in the parsed profile |
| `error` | `string \| null` | Error description, or `null` on success |

---

### `krowi_energy_management.spp_test_fetch`

Performs a live download and parse of the SPP profile for the specified year. Does **not** modify the store state.

**Parameters (optional):**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `year` | `int` | current year | Year to fetch (2020–2040) |

**Response:**

| Field | Type | Description |
|---|---|---|
| `ok` | `bool` | `true` if the profile was successfully downloaded and parsed |
| `year` | `int` | Year that was fetched |
| `http_status` | `int \| null` | HTTP status code from the download |
| `date_count` | `int \| null` | Number of dates parsed, or `null` on failure |
| `has_today` | `bool \| null` | `true` if today's date is in the parsed data |
| `first_date` | `string \| null` | First date in the parsed profile |
| `last_date` | `string \| null` | Last date in the parsed profile |
| `error` | `string \| null` | Error description, or `null` on success |

---

## Persistent Notifications

The integration creates HA persistent notifications for conditions that affect sensor availability or indicate degraded operation. All notifications appear in the HA notification bell and can be dismissed manually. Failure notifications are automatically dismissed when the underlying issue resolves.

### RLP / SPP profile notifications (electricity entry)

| Notification ID | Condition | Repeats? |
|---|---|---|
| `krowi_rlp_load_failed` | RLP download or parse failure at startup or year rollover | Every occurrence |
| `krowi_rlp_today_missing` | RLP profile loaded but today's date absent from weights | Every occurrence |
| `krowi_rlp_prefetch_failed` | Dec 26–31 nightly pre-fetch of next year's RLP profile fails | Every midnight until resolved |
| `krowi_rlp_prefetch_success` | Dec 26–31 pre-fetch of next year's RLP profile succeeds | Once per session |
| `krowi_spp_load_failed` | SPP download or parse failure at startup or year rollover | Every occurrence |
| `krowi_spp_today_missing` | SPP profile loaded but today's date absent from weights | Every occurrence |
| `krowi_spp_prefetch_failed` | Dec 26–31 nightly pre-fetch of next year's SPP profile fails | Every midnight until resolved |
| `krowi_spp_prefetch_success` | Dec 26–31 pre-fetch of next year's SPP profile succeeds | Once per session |

The `load_failed` and `today_missing` notifications are dismissed automatically when the profile is next successfully loaded from cache or downloaded.

---

## HA Energy Dashboard Compatibility

The following sensors can be used directly in the HA Energy Dashboard:

| Dashboard slot | Sensor | Unit |
|---|---|---|
| Electricity price (import) | `sensor.electricity_current_price_import_eur` | EUR/kWh |
| Electricity price (export) | `sensor.electricity_current_price_export_eur` | EUR/kWh |
| Gas price | `sensor.gas_current_price_eur` | EUR/kWh |
| Gas consumption | `sensor.gas_consumption_kwh` | kWh (`total_increasing`, `device_class: energy`) |

The `*_eur` bridge sensors exist solely because the HA Energy Dashboard requires `EUR/kWh`. All internal computations use `c€/kWh`.

---

## Failure Modes

### Nord Pool API (`dataportal-api.nordpoolgroup.com`)

- **HTTP error or timeout on fetch:** logged at `ERROR`; `current_price` remains at its last value until the next 15-min tick dispatches another fetch attempt.
- **No matching slot in today's cache:** `current_price = None`; `electricity_spot_current_price` and any derived sensors become `unavailable`.
- **API unavailable all day:** midnight snapshot is skipped (no `None` value written to buffer); the day is backfilled on next startup.
- **Backfill fetch failure for a specific date:** silently skipped; retry scheduled 60 s later, then on every subsequent startup until the gap is filled.

### Synergrid RLP/SPP profile download (`synergrid.be`)

- **Download or parse failure at startup:** A persistent HA notification (`krowi_rlp_load_failed` / `krowi_spp_load_failed`) is created with error details. `available = False`; weighted sensors fall back to unweighted means. Restart HA to retry.
- **Download or parse failure at year rollover (Jan 1):** Same notification, message indicates sensors are falling back to unweighted means. No restart required — stores will retry on the next HA reload.
- **Profile loaded but today's date not present in weights:** A `krowi_rlp_today_missing` / `krowi_spp_today_missing` notification is created. Only today's slot uses the unweighted fallback; historical buffer values are unaffected. Dismissed automatically when resolved.
- **Dec 26–31 pre-fetch failure:** A `krowi_rlp_prefetch_failed` / `krowi_spp_prefetch_failed` notification is created each midnight until the fetch succeeds or the year rolls over.

### Elindus TTF DAM API (`mijn.elindus.be`)

- **HTTP error or timeout:** logged at `ERROR`; last known `today_price` and `average` remain until next fetch; sensors become `unavailable` only if no prior fetch succeeded.
- **Today's data not yet published** (e.g. shortly after midnight): `data_is_fresh = False`; retried every 30 minutes until the current day's point appears.
- **Stale data** (last data point is yesterday): `data_is_fresh = False`; sensors remain available with yesterday's value until fresh data arrives.

### Atrias GCV API (`api.atrias.be`)

- **404 for current target month** (file not yet published, typically during the first week of a new month): silently skipped; retried at 06:00 daily.
- **Network error or HTTP 5xx:** logged at `WARNING`; retried at 06:00. `gas_calorific_value` sensor uses the most recent available value from history; gas consumption and cost sensors remain available with potentially stale GCV.
- **Zone not found in CSV:** logged at `WARNING`; `gcv = None`; all GCV-dependent sensors (`gas_current_price_m3`, `gas_consumption_kwh`, `gas_total_cost`) become `unavailable`.

### pyxlsb dependency

- **Install failure:** RLPStore cannot parse the `.xlsb` file; all RLP-weighted sensors are permanently `unavailable` until the package is available and HA is restarted.

### P1 meter / gas meter entity unavailable

- Cost accumulator sensors skip the tick silently (no exception, no logging at warning level).
- `_last_kwh` / `_last_m3` is not updated, so no double-counting occurs when the entity comes back online.

### Entity renamed via HA UI

Renaming any entity belonging to a Krowi config entry is detected by an entity-registry listener. A **Repairs issue** (`entity_renamed_{entry_id}`) is raised with severity `WARNING`. The sensors tracking the renamed entity will use a stale entity ID until the integration is reloaded or HA is restarted. **Fix:** reload the affected config entry or restart HA.

---

## Dashboard Cards

### Gas price breakdown

```yaml
type: markdown
content: >
  {% set spot = states('sensor.gas_spot_today_price') | float(0) %}
  {% set t = states('number.gas_tariff_transport') | float(0) %}
  {% set d = states('number.gas_tariff_distribution') | float(0) %}
  {% set e = states('number.gas_tariff_excise_duty') | float(0) %}
  {% set c = states('number.gas_tariff_energy_contribution') | float(0) %}
  {% set surcharge = states('sensor.gas_tariff_total_surcharge') | float(0) %}
  {% set vat = states('number.gas_vat') | float(0) %}
  {% set pre_vat = (spot + surcharge) | round(5) %}
  {% set price = states('sensor.gas_current_price') | float(0) %}

  **Gas price breakdown (c€/kWh)**

  **Surcharges:**
  - {{ state_attr('number.gas_tariff_transport', 'friendly_name') }}: **{{ '%.5f' | format(t) }}**
  - {{ state_attr('number.gas_tariff_distribution', 'friendly_name') }}: **{{ '%.5f' | format(d) }}**
  - {{ state_attr('number.gas_tariff_excise_duty', 'friendly_name') }}: **{{ '%.5f' | format(e) }}**
  - {{ state_attr('number.gas_tariff_energy_contribution', 'friendly_name') }}: **{{ '%.5f' | format(c) }}**

  **Total surcharge: {{ '%.5f' | format(surcharge) }}**

  **Spot:**
  - {{ state_attr('sensor.gas_spot_today_price', 'friendly_name') }}: **{{ '%.5f' | format(spot) }}**

  **Pre-VAT: {{ '%.5f' | format(pre_vat) }}**
  × {{ (1 + vat / 100) | round(4) }} (VAT {{ vat }}%)

  ---

  **Current gas price: {{ '%.5f' | format(price) }} c€/kWh**
```

### Electricity import price breakdown

```yaml
type: markdown
content: >
  {% set spot = states('sensor.electricity_spot_current_price') | float(0) %}
  {% set g = states('number.electricity_tariff_green_energy_contribution') | float(0) %}
  {% set dt = states('number.electricity_tariff_distribution_transport') | float(0) %}
  {% set ex = states('number.electricity_tariff_excise_duty') | float(0) %}
  {% set ec = states('number.electricity_tariff_energy_contribution') | float(0) %}
  {% set surcharge = states('sensor.electricity_tariff_total_surcharge') | float(0) %}
  {% set vat = states('number.electricity_vat') | float(0) %}
  {% set pre_vat = (spot + surcharge) | round(5) %}
  {% set price = states('sensor.electricity_current_price_import') | float(0) %}

  **Electricity import price breakdown (c€/kWh)**

  **Surcharges:**
  - {{ state_attr('number.electricity_tariff_green_energy_contribution', 'friendly_name') }}: **{{ '%.5f' | format(g) }}**
  - {{ state_attr('number.electricity_tariff_distribution_transport', 'friendly_name') }}: **{{ '%.5f' | format(dt) }}**
  - {{ state_attr('number.electricity_tariff_excise_duty', 'friendly_name') }}: **{{ '%.5f' | format(ex) }}**
  - {{ state_attr('number.electricity_tariff_energy_contribution', 'friendly_name') }}: **{{ '%.5f' | format(ec) }}**

  **Total surcharge: {{ '%.5f' | format(surcharge) }}**

  **Spot:**
  - {{ state_attr('sensor.electricity_spot_current_price', 'friendly_name') }}: **{{ '%.5f' | format(spot) }}**

  **Pre-VAT: {{ '%.5f' | format(pre_vat) }}**
  × {{ (1 + vat / 100) | round(4) }} (VAT {{ vat }}%)

  ---

  **Current import price: {{ '%.5f' | format(price) }} c€/kWh**
```

---

## Known Limitations

- **On first install the Nord Pool backfill runs at startup.** The store fetches up to one calendar month of historical daily averages (unweighted, RLP-weighted, SPP-weighted) in a single sequential pass at startup. This typically completes within a minute. Supplier price sensors are unavailable only if today's Nord Pool prices cannot be fetched (API unreachable), not because the historical buffer is incomplete. Individual backfill failures for specific dates are retried after 60 seconds and on every subsequent startup.
- **Supplier import price uses a rolling calendar-month window, not a strict calendar month.** Early in a new month the window still contains prices from the prior month. This mirrors Mega's own mid-month estimation approach and is unavoidable without waiting for month-end data.
- **GCV is always one month behind.** Atrias publishes month M's GCV in early month M+1. The `gas_current_price_m3` and `gas_consumption_kwh` sensors use the prior month's calorific value.
- **Entity IDs are pinned to UID constants and must not be renamed via the HA UI.** Doing so raises a Repairs issue and breaks reactive sensor tracking until the next reload.

---

## Store Analysis

Detailed findings per store, produced during a code review on 2026-05-06.

### NordpoolBeStore

**Redundant tomorrow fetch at 13:00** — `_on_tick` fires at `13:00:01` (minute=0, second=1) and `_on_thirteen` fires at `13:01:00`. Both spawn a `_do_tomorrow_fetch` task within one second of each other. One of the two triggers is redundant.

**No HTTP timeout** — `_async_fetch` calls `session.get(url)` with no timeout. A hung connection from the Nord Pool API holds the async slot indefinitely. All four daily tick dispatches would pile up behind it.

**Startup trim without save** — `async_start` calls `_trim_buffer()` to remove stale entries from all three in-memory buffers, but omits the matching `_save_buffer()` / `_save_rlp_buffer()` / `_save_spp_buffer()` calls. Trimmed entries persisted in HA Storage and were reloaded again on the next restart, causing the trim to run on every startup without ever shrinking the stored file. Fixed alongside the GCV save fix.

**`low_price` semantics mismatch with README** — The Configuration table describes "Low price cutoff" as a "Threshold (c€/kWh) below which `low_price` is `true`", but the code computes `current_price < average * cutoff`. With the default `1.0` this means "below today's average". The behaviour is correct and useful; the documentation is wrong.

**Year boundary — RLP/SPP weights go stale silently** — `NordpoolBeStore` holds references to `_rlp_store` and `_spp_store` which are loaded once at startup, keyed to the year. If HA runs continuously over 1 January, new-year dates are absent from those stores. `_compute_rlp_avg` / `_compute_spp_avg` fall back to the unweighted mean with no log message or signal.

---

### TtfDamStore

**Concurrent fetch at midnight** — `_on_midnight` fires at `00:00:01` (hour=0, minute=0, second=1) and `_on_tick` fires at `00:00:01` (minute=0, second=1) as well. Both schedule `async_fetch` concurrently at the exact same moment. Because `_on_midnight` resets `_data_is_fresh = False` first and `_on_tick` guards on `not self._data_is_fresh`, this is likely benign in practice, but two tasks are still spawned.

**`date.today()` instead of `dt_utils.now().date()`** — Belgium is UTC+1 (winter) / UTC+2 (summer). `date.today()` returns the system/UTC date. The freshness check `last_date == today` can evaluate to `False` for 1–2 hours after Belgian midnight even when today's data has already been published, causing unnecessary retries.

**No persistence** — `TtfDamStore` is fully stateless. After a restart with the Elindus API temporarily unreachable, both `gas_spot_today_price` and `gas_spot_average_price` are `unavailable` until the first successful fetch. Every other store persists at least some data.

**No HTTP timeout** — same risk as `NordpoolBeStore`.

---

### GcvStore

**`verify_ssl=False`** — SSL certificate validation is disabled for all requests to the Atrias API. This is a security vulnerability (OWASP A02: Cryptographic Failures / MITM). Atrias is a regulated Belgian grid operator and their API carries a valid certificate.

**`date.today()` vs `dt_utils.now().date()`** — same timezone issue as `TtfDamStore`. The `data_is_fresh` flag's semantics are calendar-month-relative, so the impact is minor, but `_target_month` and `_last_12_targets` both call `date.today()` and would benefit from consistent use of `dt_utils.now().date()`.

**Sequential gap-fill at startup** — on first install, `_fill_missing_history` fetches up to 12 months sequentially. This is 12 network round-trips in series before any sensor state is dispatched. Acceptable for a monthly store, but worth noting.

**`_save_history` awaited inside loop; missing save after prune** — `_fill_missing_history` awaited `_save_history()` inside the loop per fetched month (up to 12 writes on first install), and the post-loop save was guarded by `if missing:`, meaning a prune-only run (all months already cached but history oversized) never wrote back. Fixed: in-loop save removed, post-loop save is now unconditional. Fixed in 0.0.31.

---

### SynergridRLPStore & SynergridSPPStore

**Year-boundary handling** — both stores now subscribe to a midnight time-change listener and detect year changes at `00:00:01` on 1 January. The storage key is swapped to the new year and the profile is reloaded from cache or re-downloaded. From 26–31 December, a daily midnight check attempts to pre-fetch the next year's profile and sends HA notifications on success or failure. Fixed in 0.0.31.

**No retry after startup download failure** — if the Synergrid download fails at HA startup (network error, file not yet published), `available = False` and the store does not retry until the next HA restart or reload. A persistent notification is created with details.

**No HTTP timeout** — same risk as the other stores.

**`SynergridSPPStore` cache validation is looser than `SynergridRLPStore`** — `RLPStore` invalidates its cache when the configured DSO name changes (the cache stores `{"dso": "...", "weights": {...}}`). `SPPStore` is correctly DSO-agnostic, but its `_async_load` only checks `isinstance(raw, dict)` with no format guard, so a corrupted or old-format cache entry would silently produce bad weights.

---

## TODO

| Priority | Item | Store(s) affected |
|---|---|---|
| High | Add HTTP timeouts to fetch calls | `NordpoolBeStore`, `TtfDamStore`, `GcvStore` |
| Medium | Replace `date.today()` with `dt_utils.now().date()` | `TtfDamStore`, `GcvStore` |
| Medium | Concurrent fetch race at midnight | `TtfDamStore` |
| Medium | Redundant tomorrow fetch at 13:00 | `NordpoolBeStore` |
| Low | Persist last-known TTF DAM prices across restarts | `TtfDamStore` |
| Low | Fix `low_price` / cutoff documentation | README |

### High priority

- **Add HTTP timeouts to all store fetch calls** — `NordpoolBeStore`, `TtfDamStore`, and `GcvStore` use `session.get(url)` with no timeout. A hung connection blocks the event loop slot indefinitely.

### Medium priority

- **Replace `date.today()` with `dt_utils.now().date()` in `TtfDamStore` and `GcvStore`** — Belgium is UTC+1/+2. Using `date.today()` (system/UTC time) for freshness checks causes off-by-one errors of 1–2 hours around Belgian midnight.
- **Concurrent fetch race at midnight in `TtfDamStore`** — `_on_midnight` and `_on_tick` both fire at `00:00:01` (hour=0, minute=0, second=1), spawning two concurrent fetch tasks. The `_on_tick` handler should skip the fetch when `_on_midnight` has already scheduled one, or the tick handler should guard on `not self._data_is_fresh` only (which it already does — the midnight handler resets the flag first, so this is likely benign but worth confirming).
- **Redundant tomorrow fetch at 13:00 in `NordpoolBeStore`** — `_on_tick` fires at `13:00:01` (minute=0, second=1) and already retries the tomorrow fetch via `_do_tomorrow_fetch`; `_on_thirteen` fires one second later at `13:01:00` and does the same thing. One of the two triggers is redundant.

### Low priority

- **Persist last-known TTF DAM prices in `TtfDamStore`** — currently stateless; after a restart with the Elindus API unreachable, both gas spot sensors are `unavailable` until the first successful fetch. Persisting `today_price` and `average` to HA Storage (same pattern as `GcvStore`) would keep sensors available across restarts.
- **Fix `low_price` description in README** — the "Low price cutoff" option is documented as a "threshold in c€/kWh" but the code computes `current_price < average * cutoff`. With the default `1.0` the meaning is "below today's average". The option description and this README should reflect the actual multiplier semantics.
