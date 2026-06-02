# Changelog

## 0.0.32 (2026-06-02)

### New sensors
- `gas_spot_month_average_price` — Calendar-month-to-date average TTF DAM price in c€/kWh. Complements the existing rolling-30-day average sensor and matches the billing period used by Belgian gas suppliers.

### New features
- **Configurable Atrias GCV subscription key** — The Atrias API subscription key can now be changed from the gas entry's options flow without a HACS update. Pre-filled with the known public default so existing installs are unaffected.
- **Persistent notifications for fetch failures** — When the TTF DAM, Nord Pool BE, or GCV API cannot be reached, a persistent notification is created in HA. It is automatically dismissed on the next successful fetch.

### Improvements
- **TTF DAM store persistence** — Daily TTF DAM prices are now persisted to HA Storage (`krowi_energy_management_ttf_dam_daily`). Gas spot sensors survive HA restarts even if the Elindus API is temporarily unreachable.
- **TTF DAM rolling average** — The rolling ~30-day average (`gas_spot_average_price`) is now computed locally from the persisted buffer instead of trusting the opaque `statistics.averagePrice` field in the Elindus API response.
- **Timezone fix** — All date calculations in `TtfDamStore` now use `dt_utils.now().date()` (honouring HA's configured timezone) instead of `date.today()` (UTC/system time). Prevents stale-data issues on Docker HA with a non-UTC local timezone.
- **Concurrent fetch guard** — A `_fetch_in_flight` flag prevents double-fetches when the midnight and 30-minute tick handlers fire at the same second (00:00:01).
- **Unix ms → local date fix** — API timestamps are converted to local date via `dt_utils.as_local()` before taking `.date()`, avoiding off-by-one date errors near midnight for UTC+1/+2 timezones.

### Internal
- Added `.gitignore` to exclude `__pycache__` and `.pyc` files from the repository.
- Updated and expanded `TtfDamStore` test suite to cover buffer persistence, rolling/month averages, freshness, and timezone conversion.

---

## 0.0.31 and earlier

See git history.
