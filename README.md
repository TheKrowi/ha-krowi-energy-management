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

**Fetch schedule:** Once per year on first install (or cache miss). The parsed data is persisted in HA Storage under key `krowi_energy_management_rlp_{year}`. There is **no automatic annual renewal** — it reloads the next year's file when the new year begins and the cache misses.

**Dependency:** `pyxlsb>=1.0.10` (declared in `manifest.json`).

---

### SynergridSPPStore

**Source:** `https://www.synergrid.be/images/downloads/SLP-RLP-SPP/{year}/SPP_ex-ante_and_ex-post_{year}.xlsx`  
**Delivers data to:** `electricity_spot_average_price_spp`, supplier export price sensors

Downloads and parses the annual Synergrid SPP ex-ante solar production profile. Provides 96 quarter-hour weight values per calendar day (zero at night, peak at noon).

**Fetch schedule:** Same as RLPStore — once per year, cached in HA Storage under `krowi_energy_management_spp_{year}`. Parsed using stdlib (`zipfile` + `xml.etree.ElementTree`), no extra dependency.

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

- **Download failure at startup:** logged at `WARNING`; `rlp_store.available = False`; `electricity_spot_average_price_rlp`, `electricity_spot_average_price_spp`, and all supplier price sensors become `unavailable`.
- **Cached data present but today not in cache (year rollover):** triggers a fresh download attempt.
- **No retry after failure:** the next attempt is at the next HA restart or reload. This is intentional — the file is a static annual profile.

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

**`_save_history` awaited inside loop** — `_fill_missing_history` awaits `_save_history()` after each successful month fetch. On a first-install gap-fill of 12 months, this results in up to 12 storage writes. A single save after the loop would be sufficient.

---

### SynergridRLPStore & SynergridSPPStore

**No year-boundary handling** — both stores load once at startup, keyed to `date.today().year`. A HA instance running continuously over 1 January retains the prior year's weights indefinitely. Dates in the new year are absent; `NordpoolBeStore` silently falls back to unweighted means for all RLP/SPP-dependent sensors.

**No retry after download failure** — a transient network error at startup, or after a year rollover, leaves `available = False` permanently until the next HA restart. The annual profile files are static once published; a single retry after 60 s (via `async_call_later`) would cover most transient failures.

**No HTTP timeout** — same risk as the other stores.

**`SynergridSPPStore` cache validation is looser than `SynergridRLPStore`** — `RLPStore` invalidates its cache when the configured DSO name changes (the cache stores `{"dso": "...", "weights": {...}}`). `SPPStore` is correctly DSO-agnostic, but its `_async_load` only checks `isinstance(raw, dict)` with no format guard, so a corrupted or old-format cache entry would silently produce bad weights.

---

## TODO

| Priority | Item | Store(s) affected |
|---|---|---|
| ~~High~~ | ~~Remove `verify_ssl=False`~~ | ~~`GcvStore`~~ |
| High | Add HTTP timeouts to fetch calls | `NordpoolBeStore`, `TtfDamStore`, `GcvStore` |
| Medium | Replace `date.today()` with `dt_utils.now().date()` | `TtfDamStore`, `GcvStore` |
| Medium | Year-boundary handling (auto-reload on 1 January) | `SynergridRLPStore`, `SynergridSPPStore` |
| Medium | Concurrent fetch race at midnight | `TtfDamStore` |
| Medium | Redundant tomorrow fetch at 13:00 | `NordpoolBeStore` |
| Low | Persist last-known TTF DAM prices across restarts | `TtfDamStore` |
| Low | Fix `low_price` / cutoff documentation | README |
| Low | Save GCV history once after gap-fill loop, not per-month | `GcvStore` |

### High priority

- ~~**Remove `verify_ssl=False` in `GcvStore`**~~ — ✅ Fixed in 0.0.30. The root cause was a missing GoDaddy G2 intermediate certificate in Atrias's TLS handshake. The fix embeds the intermediate PEM and builds a custom SSL context, restoring full chain verification. Three HA diagnostic actions (`gcv_test_connection`, `gcv_test_fetch`, `gcv_store_state`) were also added.
- **Add HTTP timeouts to all store fetch calls** — `NordpoolBeStore`, `TtfDamStore`, and `GcvStore` use `session.get(url)` with no timeout. A hung connection blocks the event loop slot indefinitely.

### Medium priority

- **Replace `date.today()` with `dt_utils.now().date()` in `TtfDamStore` and `GcvStore`** — Belgium is UTC+1/+2. Using `date.today()` (system/UTC time) for freshness checks causes off-by-one errors of 1–2 hours around Belgian midnight.
- **Year-boundary handling for `SynergridRLPStore` and `SynergridSPPStore`** — both stores are loaded once at startup, keyed to the current year. If HA runs continuously over 1 January without a restart, new-year dates are not in the cache and `NordpoolBeStore` silently falls back to unweighted averages for RLP/SPP-weighted sensors. A `async_track_time_change` at `00:00:01` on 1 January should trigger a re-download for the new year.
- **Concurrent fetch race at midnight in `TtfDamStore`** — `_on_midnight` and `_on_tick` both fire at `00:00:01` (hour=0, minute=0, second=1), spawning two concurrent fetch tasks. The `_on_tick` handler should skip the fetch when `_on_midnight` has already scheduled one, or the tick handler should guard on `not self._data_is_fresh` only (which it already does — the midnight handler resets the flag first, so this is likely benign but worth confirming).
- **Redundant tomorrow fetch at 13:00 in `NordpoolBeStore`** — `_on_tick` fires at `13:00:01` (minute=0, second=1) and already retries the tomorrow fetch via `_do_tomorrow_fetch`; `_on_thirteen` fires one second later at `13:01:00` and does the same thing. One of the two triggers is redundant.

### Low priority

- **Persist last-known TTF DAM prices in `TtfDamStore`** — currently stateless; after a restart with the Elindus API unreachable, both gas spot sensors are `unavailable` until the first successful fetch. Persisting `today_price` and `average` to HA Storage (same pattern as `GcvStore`) would keep sensors available across restarts.
- **Fix `low_price` description in README** — the "Low price cutoff" option is documented as a "threshold in c€/kWh" but the code computes `current_price < average * cutoff`. With the default `1.0` the meaning is "below today's average". The option description and this README should reflect the actual multiplier semantics.
- **Save GCV history once after gap-fill loop** — `_fill_missing_history` currently awaits `_save_history()` inside the loop for each month fetched. A single save after the loop completes is sufficient and avoids redundant writes.
