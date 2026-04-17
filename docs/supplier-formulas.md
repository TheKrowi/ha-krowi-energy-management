# Supplier Price Formulas

This document describes how supplier-specific electricity prices are calculated from the EPEX SPOT monthly average.

## Overview

All supplier price sensors use the **RLP-weighted** EPEX SPOT monthly average (`electricity_spot_average_price_rlp`) as their base price. This is the calendar-month rolling average weighted by the Synergrid RLP0N consumption profile — the same weighting that suppliers use when settling with the grid.

The sensors are **unavailable** when the RLP-weighted average is not yet populated (typically for ~30 days after first install while the buffer fills).

---

## Mega (tariefkaart 12/2025)

See [docs/suppliers/mega.md](suppliers/mega.md) for full details.

### Import price (`electricity_mega_import_price`)

$$
P_{\text{import}} = \bigl(\text{EPEX}_{\text{RLP}} \times 1.061 + \text{surcharge}\bigr) \times \left(1 + \frac{\text{VAT}}{100}\right)
$$

**Unit:** c€/kWh, VAT inclusive. EUR/kWh variant: divide by 100.

---

### Export price (`electricity_mega_export_price`)

$$
P_{\text{export}} = \text{EPEX}_{\text{RLP}} \times 0.94 - 1.7
$$

| Variable | Source | Notes |
|---|---|---|
| $\text{EPEX}_{\text{RLP}}$ | `electricity_spot_average_price_rlp` | c€/kWh, RLP-weighted monthly average |
| $0.94$ | Mega buy-back factor | Mega retains 6% margin on export |
| $-1.7$ | Fixed deduction (c€/kWh) | Administrative/handling fee |

**Unit:** c€/kWh, VAT exempt (BTW-vrij).

The EUR/kWh variant (`electricity_mega_export_price_eur`) is:

$$
P_{\text{export, EUR}} = P_{\text{export}} \div 100
$$

---

## Adding a new supplier

Add an entry to `ELECTRICITY_SUPPLIER_CATALOG` in `const.py`:

```python
"slug": {
    "name": "Display Name",
    "import": {
        "epex_multiplier": <float>,       # multiply EPEX_RLP by this
        "epex_offset_cEur_kwh": <float>,  # add after multiplication (before surcharge+VAT)
        "includes_surcharge": False,       # if True, surcharge is not added separately
        "vat_exempt": False,               # if True, VAT is not applied
    },
    "export": {
        "epex_multiplier": <float>,
        "epex_offset_cEur_kwh": <float>,
        "includes_surcharge": False,
        "vat_exempt": True,               # export is typically VAT exempt
    },
},
```

The general import formula is:

$$
P_{\text{import}} = \bigl(\text{EPEX}_{\text{RLP}} \times m + o + \text{surcharge}_{?}\bigr) \times (1 + \text{VAT}_{?}/100)
$$

Where $m$ = `epex_multiplier`, $o$ = `epex_offset_cEur_kwh`, and the surcharge/VAT terms are applied only when `includes_surcharge = False` / `vat_exempt = False` respectively.

The general export formula is:

$$
P_{\text{export}} = \text{EPEX}_{\text{RLP}} \times m + o
$$
