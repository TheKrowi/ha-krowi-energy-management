## Why

`sensor.electricity_spot_average_price` currently exposes only today's mean of 96 × 15-min slots, which is a poor input for export price formulas that Belgian dynamic-contract suppliers compute against a calendar-month average. Gas already uses a rolling calendar-month average (via a single `?from/to` API call); electricity should match that quality.

## What Changes

- `sensor.electricity_spot_average_price` state changes from "today's daily mean" to "rolling calendar-month average (buffer + today-live)" — same entity ID, same unit (`c€/kWh`), better value.
- `NordpoolBeStore` gains a `_daily_avg_buffer: dict[date, float]` persisted via `homeassistant.helpers.storage.Store`, a gap-fill backfill on startup (up to 29 sequential API calls on first install, zero thereafter), and a midnight snapshot that captures yesterday's average for free before fetching the new day.
- A `history` attribute is added to `sensor.electricity_spot_average_price` exposing the buffer as `{"YYYY-MM-DD": float, ...}` for future graphing.
- The `average` attribute previously duplicated on `sensor.electricity_spot_current_price` is removed (it was the daily average, now redundant/misleading).
- Display names for `sensor.electricity_spot_average_price` are updated from "Daily average price (EPEX SPOT)" to "Monthly average price (EPEX SPOT)".
- `DEFAULT_EXPORT_TEMPLATE` in `const.py` continues to reference `sensor.electricity_spot_average_price` — no change needed since the entity ID is stable; the value it reads simply improves.

## Capabilities

### New Capabilities

- `electricity-monthly-average-store`: Rolling calendar-month daily-average buffer inside `NordpoolBeStore` — persisted storage, startup gap-fill, midnight snapshot, trim logic.

### Modified Capabilities

- `electricity-spot-sensors`: `sensor.electricity_spot_average_price` changes state semantics (daily → monthly average) and gains a `history` attribute; `sensor.electricity_spot_current_price` loses the redundant `average` state attribute.
- `nordpool-be-store`: Store gains `monthly_average` property, `_daily_avg_buffer`, persistence via HA Storage, and updated midnight/startup lifecycle.

## Impact

- `nordpool_store.py`: main changes — buffer, storage, gap-fill, snapshot, new `monthly_average` property.
- `sensor.py`: `ElectricitySpotAverageSensor` reads `store.monthly_average` instead of `store.average`; adds `history` attribute. `ElectricitySpotCurrentPriceSensor` drops `average` from `extra_state_attributes`.
- `const.py`: display name strings for `UID_ELECTRICITY_SPOT_AVERAGE_PRICE` updated in both languages.
- `manifest.json`: no dependency changes (`dateutil` already present via gas; HA Storage is a core helper).
- First-install UX: up to ~30 s at startup for backfill (sequential unauthenticated calls, well within Nord Pool burst limits).
