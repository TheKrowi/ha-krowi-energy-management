## Why

The four spot sensor display names are generic and don't clearly communicate their data source or time window. The gas average sensor uses a fixed 30-day window where a calendar-month-aligned rolling window (`relativedelta(months=1)`) better reflects how Belgian gas suppliers calculate monthly pricing and self-adjusts for shorter months like February.

## What Changes

- Rename `electricity_spot_current_price` display name to "Current price (EPEX SPOT)" / "Huidige prijs (EPEX SPOT)"
- Rename `electricity_spot_average_price` display name to "Daily average price (EPEX SPOT)" / "Gemiddelde dagprijs (EPEX SPOT)"
- Rename `gas_spot_today_price` display name to "Daily price (TTF DAM)" / "Dagprijs (TTF DAM)"
- Rename `gas_spot_average_price` display name to "Monthly average price (TTF DAM)" / "Gemiddelde maandprijs (TTF DAM)"
- Change `TtfDamStore` fetch window from `timedelta(days=30)` to `relativedelta(months=1)` so the window self-adjusts per calendar month (28–31 days)

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `electricity-spot-sensors`: Display names for both sensors change (EN + NL)
- `gas-spot-sensors`: Display names for both sensors change (EN + NL); `gas_spot_average_price` description changes from "30-day average" to "rolling month average"
- `ttf-dam-store`: Fetch window changes from fixed `timedelta(days=30)` to calendar-month-aligned `relativedelta(months=1)`

## Impact

- `custom_components/krowi_energy_management/const.py` — 8 `NAMES` entries updated
- `custom_components/krowi_energy_management/ttf_dam_store.py` — fetch window logic updated, `dateutil.relativedelta` import added
- No entity IDs, unique IDs, or platform structure changes — existing HA installations will see only a display name update
