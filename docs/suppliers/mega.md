# Mega — Tariefkaart 12/2025

**Product:** Wikipower (Variabel) — 100% groene elektriciteit  
**Region:** Vlaanderen  
**Source:** `tarrif_cards/electricity/Mega-NL-EL-B2C-VL-122025-WP1025-Var.extracted.json`

---

## Import price (`electricity_mega_import_price`)

### Formula

$$
P_{\text{import}} = \bigl(\text{EPEX}_{\text{RLP}} \times 1.061 + \text{surcharge}\bigr) \times \left(1 + \frac{\text{VAT}}{100}\right)
$$

**Unit:** c€/kWh, VAT inclusive.

The EUR/kWh variant (`electricity_mega_import_price_eur`):

$$
P_{\text{import, EUR}} = P_{\text{import}} \div 100
$$

### Variables

| Variable | Source | Notes |
|---|---|---|
| $\text{EPEX}_{\text{RLP}}$ | `sensor.electricity_spot_average_price_rlp` | c€/kWh, RLP-weighted rolling monthly average; sensor mirrors `NordpoolBeStore.monthly_average_rlp` |
| $1.061$ | Mega multiplier (hardcoded) | Covers settlement margin, imbalance, etc. |
| $\text{surcharge}$ | `sensor.electricity_tariff_total_surcharge` | c€/kWh, sum of all non-VAT tariff components; import sensor subscribes to state changes |
| $\text{VAT}$ | `number.electricity_vat` | %; import sensor subscribes to state changes |

### Tariff card source

> *"Enkelvoudige meter: Epex \* 1,061"* (excl. BTW)  
> *"De variabele elektriciteitsprijs wordt maandelijks geïndexeerd … gewogen met het RLP-profiel (gepubliceerd door Synergrid)."*

VAT: 6% (residential Flanders).

### Estimation nuances

**Mid-month data gap (acknowledged by Mega)**

Mega settles on a strict calendar month, but not all quarter-hour EPEX data points are available before month-end. The tariff card explicitly states:

> *"Als sommige QH-gegevens nog niet beschikbaar zijn op de berekeningsdatum, wordt de factuur opgesteld op basis van de beschikbare gegevens en automatisch rechtgezet zodra de ontbrekende gegevens ontvangen zijn."*

Mega itself estimates mid-month and issues a corrected invoice once all data arrives. The sensor converges toward the final value as the month progresses — this is unavoidable and mirrors Mega's own approach.

**Rolling 30-day window vs. strict calendar month**

The RLP-weighted average uses a rolling ~30-day window (today minus one calendar month), not a strict calendar month. Early in a new month the window still contains prices from the previous month.

This is intentional: the sensor's purpose is **live price estimation**, for which a rolling window is a stable and responsive signal. It is not designed to reproduce the exact end-of-month invoice figure. Divergence from the final Mega bill is largest in the first ~2 weeks of a new month.

**RLP profile is a normative annual estimate**

Synergrid publishes the `RLP0N` residential consumption profile annually in advance; it is never retroactively corrected. Unlike SPP (see export), there is no ex-post variant with revised values. This is not a meaningful accuracy risk: real residential load shapes are very stable year over year, and Mega uses this same published profile for settlement.

### Catalog entry (`const.py`)

```python
"mega": {
    "name": "Mega",
    "import": {
        "epex_multiplier": 1.061,
        "epex_offset_cEur_kwh": 0.0,
        "includes_surcharge": False,
        "vat_exempt": False,
    },
    ...
}
```

---

## Export price (`electricity_mega_export_price`)

### Formula

$$
P_{\text{export}} = \text{EPEX}_{\text{SPP}} \times 0.94 - 1.7
$$

**Unit:** c€/kWh, VAT exempt (BTW-vrij).

The EUR/kWh variant (`electricity_mega_export_price_eur`):

$$
P_{\text{export, EUR}} = P_{\text{export}} \div 100
$$

### Variables

| Variable | Source | Notes |
|---|---|---|
| $\text{EPEX}_{\text{SPP}}$ | `sensor.electricity_spot_average_price_spp` | c€/kWh, SPP-weighted rolling monthly average; sensor mirrors `NordpoolBeStore.monthly_average_spp` |
| $0.94$ | Mega buy-back factor (hardcoded) | Mega retains 6% margin on export |
| $-1.7$ | Fixed deduction (hardcoded) | Administrative/handling fee (c€/kWh) |

### Tariff card source

> *"Het tarief is dan gebaseerd op het SPP-gewogen gemiddelde (gepubliceerd door synergrid) van de dagelijkse quoteringen Day Ahead EPEX SPOT Belgium tijdens de maand van de levering … en volgens de formule (excl. BTW): Epex SPP \* 0,94 – 1,7 c€/kWh."*

VAT: exempt (*"De injectieprijzen zijn vrijgesteld van btw."*).

### Estimation nuances

**Mid-month data gap (acknowledged by Mega)**

Same applies as import: not all QH EPEX data is available before month-end. The sensor converges toward the final invoice value as the month progresses.

**Rolling 30-day window vs. strict calendar month**

Same applies as import: the SPP-weighted average uses a rolling ~30-day window. Divergence from the final Mega invoice is largest in the first ~2 weeks of a new month.

**SPP ex-ante profile vs. Mega's ex-post settlement**

Synergrid publishes both an **ex-ante** (forward-looking, published at start of year) and an **ex-post** (backward-looking, actual production pattern, published after month-end) SPP profile. Mega's invoice settlement uses the **ex-post** profile.

The sensor uses the **ex-ante** profile because ex-post is only available after the month closes — it cannot be used for a live sensor. In practice ex-ante and ex-post shapes correlate well, but divergence can be meaningful during months with atypical solar or wind generation patterns. This is a known, unavoidable limitation.

**SPP sensor entity**

The SPP-weighted monthly average is exposed as `sensor.electricity_spot_average_price_spp`, mirroring `NordpoolBeStore.monthly_average_spp`. The export price sensor also reads `store.monthly_average_spp` directly via `SIGNAL_NORDPOOL_UPDATE` and does not depend on the SPP sensor entity. `sensor.electricity_spot_average_price_spp` exists purely as a transparency/dashboard entity — it lets users see the SPP-weighted EPEX average independently.

### Catalog entry (`const.py`)

```python
"mega": {
    ...
    "export": {
        "epex_multiplier": 0.94,
        "epex_offset_cEur_kwh": -1.7,
        "includes_surcharge": False,
        "vat_exempt": True,
    },
}
```
