## Context

Gas meters in Belgium measure in m³. The HA energy dashboard, Fluvius invoices, and the integration's existing gas pricing pipeline all operate in kWh. The bridge between the two is the Gross Calorific Value (GCV), a monthly, per-GOS-zone conversion factor published by Atrias (Belgian energy market operator) at a predictable API endpoint.

The integration already contains a `TtfDamStore` — a standalone store class that fetches, caches, and dispatches gas spot prices. The `GcvStore` follows the same pattern.

## Goals / Non-Goals

**Goals:**
- Fetch monthly GCV for the user's GOS zone from the Atrias API.
- Persist a 12-month rolling history in HA storage, surviving restarts and partial fetches.
- Expose `gas_calorific_value` (kWh/m³), `gas_current_price_m3` (€/m³), and `gas_consumption_kwh` (kWh).
- Allow GOS zone and gas meter entity to be configured via the gas options flow.

**Non-Goals:**
- Fetching GCV for multiple zones simultaneously.
- Supporting non-Belgian networks (Wallonia DNOs use the same API, but zone naming is treated as user-configured).
- Electricity or water consumption conversion.
- Exposing raw Atrias API data beyond the selected zone's GCV.

## Decisions

### Decision: Mirror TtfDamStore pattern for GcvStore
`GcvStore` follows the same lifecycle as `TtfDamStore`: instantiated in `async_setup_entry`, started via `async_start(hass)`, stopped via `async_stop()`, stored in `hass.data[DOMAIN]["gcv_store"]`. This keeps the architecture consistent and predictable.

*Alternative: DataUpdateCoordinator* — rejected because it doesn't support the targeted retry logic (daily at 06:00 while not fresh) and would couple entities to polling rather than dispatch.

### Decision: Target file is always prior month
The Atrias GCV file for month M is published in early month M+1 (typically 1–4 days in). The current month's file never exists. The store always targets `YYYY-{prior_month}.txt` and retries daily at 06:00 until it appears.

*Alternative: try current month first then fall back* — rejected; the current month file has never been observed to exist. Unnecessary 404s add latency and noise.

### Decision: Persist history via hass.helpers.storage
`hass.helpers.storage.Store` (JSON) is used to persist the `{ "YYYY-MM": gcv_value }` dict. On every start, the store loads existing history, computes the 12 target months, and fetches only the missing ones. This handles first install, restart, rate limiting, and month rollover with a single gap-fill loop.

*Alternative: hass.data only (in-memory)* — rejected; history would reset on every restart, requiring 12 API calls on every HA restart.

### Decision: Bootstrap fetches up to 12 prior months on first install
When history is empty (first install) or partially populated (interrupted bootstrap or rate limiting), the store computes the 12 most recent target months and fetches any that are missing, oldest-first. This fills history in a single startup pass without repeated manual intervention.

*Alternative: Fill history lazily (one month per month)*  — rejected; would leave the history attribute empty for up to a year after first install.

### Decision: GOS zone as config option (dropdown), not auto-detected
The zone cannot be reliably derived from a meter EAN without a lookup table that changes over time. A user-facing dropdown of all zone names from the most recent GCV file is simple and transparent. Default: `GOS FLUVIUS - LEUVEN`.

*Alternative: EAN-based auto-detection* — rejected; EAN→zone mapping is not publicly maintained in a stable, machine-readable form.

### Decision: gas_consumption_kwh tracks state changes on the meter entity
`gas_consumption_kwh` subscribes to `async_track_state_change_event` on `CONF_GAS_METER_ENTITY` and recomputes on every state change — consistent with how all other derived sensors work in this integration. The GCV factor is read from the store (not re-fetched) on each state change.

### Decision: Atrias subscription key embedded in const.py
The key (`41be1fbab53b4a80ba0d17084a338a55`) is a public sector data key embedded in publicly accessible download URLs on the Atrias website. It is not a secret. Embedding it in `const.py` is appropriate.

## Risks / Trade-offs

- **Atrias API availability** → GCV history persists in HA storage; sensors continue reporting the last known value if fetches fail. `data_is_fresh` is exposed for transparency.
- **GOS zone list may evolve** (zones added/renamed as network transitions complete) → The dropdown is populated from a hardcoded list at integration build time. Zone renames would require an integration update. Mitigation: allow free-text fallback if entered zone is not found in the fetched file (log a warning, keep last known value).
- **gas_consumption_kwh state_class** → `total_increasing` mirrors the source meter entity. If the source entity resets (meter replacement), the derived sensor will also reset. This is correct HA behavior for total-increasing sensors and energy dashboard compatibility.
- **Rate limiting** → The store only fetches at most once per day (daily retry) plus the bootstrap. Risk of hitting rate limits is negligible.

## Migration Plan

Purely additive. No existing entities, config keys, or behaviors are changed. Users with an existing gas config entry will see the new options appear in the options flow after the update. Until they configure a GOS zone, all three new sensors will be unavailable.
