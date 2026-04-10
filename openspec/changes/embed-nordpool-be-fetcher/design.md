## Context

Currently `ElectricityImportPriceSensor` reads `current_price_entity` (default `sensor.nord_pool_be_current_price`) and optionally `fx_rate_entity` from the config entry. This means users must install the Nord Pool HACS component separately, and the component is dependent on its entity IDs and attribute names remaining stable.

The Nord Pool dataportal API (`https://dataportal-api.nordpoolgroup.com/api/DayAheadPrices`) is public, unauthenticated, and returns 15-minute day-ahead prices. For Belgium the region code is `BE`, currency is `EUR`, and prices are in `EUR/MWh`. The full day (96 × 15-min slots) is available by midnight CET. Tomorrow's prices are published around 13:00 CET.

## Goals / Non-Goals

**Goals:**
- Own the entire spot price data pipeline inside `krowi_energy_management`
- Expose two new sensor entities for spot current price and spot average price
- Remove `current_price_entity`, `fx_rate_entity` from the electricity config entry
- Add `low_price_cutoff` to electricity options
- Migrate existing v1 config entries to v2 cleanly

**Non-Goals:**
- Supporting regions other than `BE` (hardcoded)
- Supporting currencies other than `EUR` (hardcoded)
- Providing a full Nord Pool replacement with all attributes (e.g. `off_peak_1`, `off_peak_2`, `peak`, `mean`)
- Replacing the gas price source (TTF DAM, separate component — unchanged)

## Decisions

### Decision: Plain store class, not DataUpdateCoordinator

**Chosen**: A plain `NordpoolBeStore` class with explicit time-event subscriptions.

**Rationale**: `DataUpdateCoordinator` is designed for periodic API polling. This store fetches at most twice per day (today at startup, tomorrow after 13:00). All 15-min price updates are cache reads. Using a coordinator would misrepresent the update pattern and poll the API unnecessarily every 15 minutes.

**Alternative considered**: `DataUpdateCoordinator` with 15-min interval — rejected because it would call the API 96× per day instead of 1-2×.

---

### Decision: Time-tick events at :00:01, :15:01, :30:01, :45:01

**Chosen**: `async_track_time_change(hass, handler, minute=[0, 15, 30, 45], second=1)`

**Rationale**: Firing 1 second past each quarter-hour boundary guarantees `dt_utils.now()` is always inside the new slot when the handler runs, avoiding off-by-one at exactly the slot boundary due to scheduler jitter. The 1-second delay is imperceptible.

**Alternative considered**: Firing at second=0 — rejected due to potential boundary ambiguity.

---

### Decision: Store lives on `hass.data[DOMAIN]["nordpool_store"]`

**Chosen**: Single store instance stored in `hass.data` under the component's domain key.

**Rationale**: The electricity config entry setup needs access to the store. Storing it in `hass.data` avoids passing it through config entry `data` and ensures it is created once and shared if multiple entries ever need it.

---

### Decision: Unit conversion at ingest time (EUR/MWh → c€/kWh)

**Chosen**: Divide `entryPerArea["BE"]` by `10` when parsing each slot during fetch.

**Rationale**: The electricity domain always uses `c€/kWh`. Converting at ingest keeps all downstream logic in a single unit, removing the need for runtime unit detection or conversion in the sensor. `EUR/MWh ÷ 10 = c€/kWh` is exact and unambiguous.

**Alternative considered**: Storing raw `EUR/MWh` and converting in the sensor — rejected because it would add conditional conversion logic and reintroduce the unit-detection complexity being removed.

---

### Decision: `low_price` computed in the store, `low_price_cutoff` stored in electricity options

**Chosen**: Store reads `low_price_cutoff` from the electricity config entry options (default `1.0`). Store computes `low_price = current_price < average * cutoff` and the spot sensors expose it as an attribute.

**Rationale**: `low_price_cutoff` is electricity-specific. Keeping it in the electricity entry options means a user can change it without reconfiguring the whole integration.

---

### Decision: Config entry migration v1 → v2

**Chosen**: Implement `async_migrate_entry` in `__init__.py`. For electricity entries: remove `current_price_entity` and `fx_rate_entity` from `data`, set `VERSION = 2`.

**Rationale**: Without migration, existing installs would have stale fields in `entry.data` that could confuse code checking for their presence.

The migration function must handle the case where the fields are absent (idempotent).

---

### Decision: `CONF_CURRENT_PRICE_ENTITY` and `CONF_FX_RATE_ENTITY` kept in `const.py` for gas

**Chosen**: Both constants remain in `const.py` because `CONF_CURRENT_PRICE_ENTITY` is still used by the gas config entry shape.

**Rationale**: The gas domain still reads a configurable TTF DAM price entity. Only the electricity domain eliminates these fields.

## Risks / Trade-offs

**[Risk] Nord Pool API endpoint changes** → The API URL and field names (`multiAreaEntries`, `deliveryStart`, `deliveryEnd`, `entryPerArea`) are hardcoded. If Nord Pool changes their API (they did once before), the store will stop working.  
→ Mitigation: Log a clear error on parse failure; set both spot sensors to `unavailable` with a meaningful message. No worse than Nord Pool HACS component breaking.

**[Risk] Tomorrow's price window is fuzzy** → Prices are "around 13:00 CET" but can be delayed. The store re-attempts on every tick from 13:00 onward until `tomorrow` data arrives, then stops.  
→ Mitigation: `tomorrow_valid = False` until data is confirmed present; sensors expose this attribute.

**[Risk] Breaking change for existing users** → Removing `current_price_entity` requires migration and breaks any user who had customised the entity ID to a non-BE source.  
→ Mitigation: Noted as a known breaking change in the proposal. Migration makes it clean for default users. Non-BE users will need to reconfigure (out of scope — this component is BE-first by design).

**[Risk] Store not yet initialised when sensor platform sets up** → `async_setup_entry` for the electricity platform runs after `__init__.py` sets up the store, but HA platform setup order is not guaranteed to be instant.  
→ Mitigation: Sensor's `async_added_to_hass` triggers an initial state read from the store (which may be empty/`None`), then reacts to the first tick. Sensors start as `unavailable` and update within at most 15 minutes (typically within the first tick after startup).

## Migration Plan

1. `__init__.py`: Add `async_migrate_entry`. For `entry.version == 1` electricity entries: strip `current_price_entity` and `fx_rate_entity` from a copy of `entry.data`, write new data, set `entry.version = 2`.
2. `config_flow.py`: Set `VERSION = 2`. Update electricity setup/options schemas.
3. `const.py`: Add `CONF_LOW_PRICE_CUTOFF`, `UID_ELECTRICITY_SPOT_CURRENT_PRICE`, `UID_ELECTRICITY_SPOT_AVERAGE_PRICE`, `DEFAULT_LOW_PRICE_CUTOFF = 1.0`. Remove `DEFAULT_ELECTRICITY_PRICE_ENTITY`.
4. `nordpool_store.py`: New file.
5. `sensor.py`: Add `ElectricitySpotCurrentPriceSensor`, `ElectricitySpotAverageSensor`. Update `ElectricityImportPriceSensor` to track the internal spot entity instead of a config-entry entity.

**Rollback**: Revert to prior commit. Users will need to reconfigure the electricity entry to re-add `current_price_entity`.

## Open Questions

- Should the `today[]` and `tomorrow[]` attribute values be rounded to 5 decimal places, or left as raw `c€/kWh` floats from the API? (Leaning toward 5dp for consistency with other sensors.)
- The export template default currently references `sensor.nord_pool_be_average_price`. Should the migration update stored `export_template` values in existing entries to reference the new `electricity_spot_average_price` entity? (Leaning yes, but only for the known default string.)
