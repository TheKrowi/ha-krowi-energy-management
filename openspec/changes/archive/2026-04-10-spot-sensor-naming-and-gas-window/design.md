## Context

The four spot sensor display names currently use generic terms ("Spot current price", "Spot average price", "Spot today price", "Spot 30-day average") that don't identify the data source or make the time window unambiguous. The owner uses NL as their HA language and has specific preferred labels from their dashboard.

The `TtfDamStore` currently requests `from = today - 30 days` as a fixed timedelta. Belgian gas suppliers calculate monthly invoices by averaging daily TTF DAM prices over the calendar month. A fixed 30-day window drifts relative to month boundaries and overestimates February's window by 2–3 days.

## Goals / Non-Goals

**Goals:**
- Source-attributed, time-window-explicit display names for all four spot sensors in both EN and NL
- Gas average fetch window aligned to one calendar month via `relativedelta(months=1)`, self-adjusting for month length

**Non-Goals:**
- No entity ID or unique ID changes — this is display-only for the naming part
- No new sensors or platforms
- No config/options flow changes

## Decisions

### Decision: Use `dateutil.relativedelta` for the month window
`timedelta` cannot express "one calendar month". `dateutil.relativedelta(months=1)` handles this correctly and clamps end-of-month overflow (e.g. March 31 → February 28/29). `python-dateutil` is part of HA's core environment — no manifest dependency change required.

**Alternative considered**: Manual month arithmetic using `date.replace()`. Rejected — more code, same result, worse readability.

### Decision: Names include source in parentheses
Each spot sensor name includes its data source in parentheses: `(EPEX SPOT)` for electricity, `(TTF DAM)` for gas. This removes ambiguity when sensors from both domains are shown side-by-side on a dashboard.

**Alternative considered**: Omit source from name, rely on device grouping. Rejected — dashboard cards don't always show device context.

### Decision: "Daily" / "Monthly" in name, not "24h" / "30-day"
`electricity_spot_average_price` is the mean of today's calendar day slots, not a rolling 24h window. "Daily average" is more accurate. `gas_spot_average_price` covers one calendar month. "Monthly average" is clearer than "30-day" and stays correct when the window is 28 days.

## Risks / Trade-offs

- **Gas average value will change slightly after deploy** — switching from fixed 30 days to `relativedelta(months=1)` will change the numerical value of `gas_spot_average_price` on the first fetch after deployment (28 vs 30 days in February, for example). Not a breaking change, but the sensor value will shift.  
  → Mitigation: cosmetic change only; no automations are expected to depend on exact gas average value.

- **Display name change in HA** — existing installations will see entity friendly names update on next HA restart. Any dashboard cards using the old friendly name as a label will auto-update (HA follows the entity name). Cards with manually overridden names are unaffected.  
  → No mitigation needed; this is the desired outcome.
