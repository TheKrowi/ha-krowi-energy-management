## ADDED Requirements

### Requirement: Supplier catalog defined in const.py
`const.py` SHALL define `ELECTRICITY_SUPPLIER_CATALOG: dict[str, dict]` mapping supplier
slugs to formula parameters. `"mega"` SHALL be the first catalog entry.

Each entry SHALL have the shape:
```python
{
    "name": str,                       # Display name (e.g. "Mega")
    "import": {
        "epex_multiplier": float,      # Applied to monthly RLP-weighted EPEX average
        "epex_offset_cEur_kwh": float, # Added after multiplier (usually 0.0)
        "includes_surcharge": bool,    # False = surcharge is added separately
        "vat_exempt": bool,            # False for import
    },
    "export": {
        "epex_multiplier": float,
        "epex_offset_cEur_kwh": float, # Negative = deduction (e.g. Mega: -1.7)
        "includes_surcharge": bool,    # False for export
        "vat_exempt": bool,            # True for export (BTW-vrij)
    },
}
```

Mega entry (source: Mega tariefkaart 12/2025):
- import: `epex_multiplier=1.061`, `epex_offset_cEur_kwh=0.0`, `includes_surcharge=False`, `vat_exempt=False`
- export: `epex_multiplier=0.94`, `epex_offset_cEur_kwh=-1.7`, `includes_surcharge=False`, `vat_exempt=True`

#### Scenario: Mega catalog entry exists
- **WHEN** `ELECTRICITY_SUPPLIER_CATALOG` is inspected at runtime
- **THEN** `"mega"` SHALL be a key and its import multiplier SHALL be `1.061`

---

### Requirement: Supplier config entry type exists
`const.py` SHALL define `DOMAIN_TYPE_ELECTRICITY_SUPPLIER = "electricity_supplier"`,
`CONF_SUPPLIER_SLUG = "supplier_slug"`, and `CONF_SUPPLIER_LABEL = "supplier_label"`.

The config flow menu SHALL include `electricity_supplier` as an option. Selecting it SHALL
present a form with a `SelectSelector` of catalog keys as `supplier_slug` and an optional
text field as `supplier_label` (defaults to the catalog entry's `name`).

No duplicate-slug check is enforced — multiple entries with the same slug are allowed.

#### Scenario: User adds Mega supplier entry
- **WHEN** user selects "electricity_supplier" in the config flow menu
- **THEN** user SHALL be presented with a slug selector containing at least `"mega"`
- **WHEN** user submits with `supplier_slug = "mega"`
- **THEN** a config entry with `domain_type = "electricity_supplier"` and `supplier_slug = "mega"` SHALL be created

---

### Requirement: Supplier config entry creates 4 sensor entities
A config entry with `domain_type = "electricity_supplier"` SHALL create exactly 4 sensor
entities. Unique IDs use the slug verbatim:

| Unique ID | Unit | VAT |
|---|---|---|
| `electricity_{slug}_import_price` | `c€/kWh` | yes |
| `electricity_{slug}_import_price_eur` | `EUR/kWh` | yes |
| `electricity_{slug}_export_price` | `c€/kWh` | no (exempt) |
| `electricity_{slug}_export_price_eur` | `EUR/kWh` | no (exempt) |

All 4 entities SHALL be assigned to a `DeviceInfo` named after `supplier_label`
(or the catalog `name` if no label was provided).

#### Scenario: Four sensors created for Mega entry
- **WHEN** a supplier config entry with `supplier_slug = "mega"` is loaded
- **THEN** sensors `electricity_mega_import_price`, `electricity_mega_import_price_eur`,
  `electricity_mega_export_price`, `electricity_mega_export_price_eur` SHALL be registered in HA

---

### Requirement: Supplier import price formula
`electricity_{slug}_import_price` SHALL compute:
`(EPEX_rlp × import_multiplier + import_offset + surcharge) × (1 + VAT/100)`
rounded to 5 decimal places.

Where:
- `EPEX_rlp` = `store.monthly_average_rlp` (c€/kWh)
- `surcharge` = state of `sensor.electricity_tariff_total_surcharge` (c€/kWh)
- `VAT` = state of `number.electricity_vat` (%)

The sensor SHALL update on `SIGNAL_NORDPOOL_UPDATE` and on state changes to surcharge and VAT.
The sensor SHALL be `unavailable` when `store.monthly_average_rlp` is `None`.

#### Scenario: Mega import price computed correctly
- **WHEN** `store.monthly_average_rlp = 10.0`, `surcharge = 5.0`, `VAT = 6.0`
- **THEN** `electricity_mega_import_price` SHALL be `round((10.0 × 1.061 + 0.0 + 5.0) × 1.06, 5)`

#### Scenario: Sensor unavailable when RLP average is None
- **WHEN** `store.monthly_average_rlp` is `None`
- **THEN** `electricity_mega_import_price` SHALL be `unavailable`

---

### Requirement: Supplier export price formula
`electricity_{slug}_export_price` SHALL compute:
`EPEX_rlp × export_multiplier + export_offset`
rounded to 5 decimal places. VAT SHALL NOT be applied (export is BTW-vrij).

The sensor SHALL be `unavailable` when `store.monthly_average_rlp` is `None`.

#### Scenario: Mega export price computed correctly
- **WHEN** `store.monthly_average_rlp = 10.0`
- **THEN** `electricity_mega_export_price` SHALL be `round(10.0 × 0.94 + (-1.7), 5)` = `7.7`

#### Scenario: Sensor unavailable when RLP average is None
- **WHEN** `store.monthly_average_rlp` is `None`
- **THEN** `electricity_mega_export_price` SHALL be `unavailable`

---

### Requirement: EUR/kWh bridge sensors for supplier
`electricity_{slug}_import_price_eur` SHALL be `import_price ÷ 100`.
`electricity_{slug}_export_price_eur` SHALL be `export_price ÷ 100`.
Both SHALL update on state changes to their respective source sensor.

#### Scenario: EUR bridge value
- **WHEN** `electricity_mega_import_price = 15.9325`
- **THEN** `electricity_mega_import_price_eur` SHALL be `0.159325`
