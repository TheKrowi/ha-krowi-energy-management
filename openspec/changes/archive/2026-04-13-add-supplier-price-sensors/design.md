## Context

The component already fetches Nord Pool BE 15-min prices via `NordpoolBeStore` and exposes
`electricity_spot_current_price` (live slot) and `electricity_spot_average_price` (rolling
30-day unweighted monthly average). Tariff numbers and a Jinja2 export-template exist for
import/export price sensors, but neither is supplier-formula-aware.

Belgian variable-rate suppliers (Mega, Eneco, …) compute the monthly EPEX commodity price
as an **RLP-weighted** average of 15-min QH prices, using weights published annually by
Synergrid. Without RLP weighting the monthly average differs by ~2-3%.

Three new building blocks are added in this change. All existing sensors are untouched.

## Goals / Non-Goals

**Goals:**
- Fetch and cache the Synergrid RLP0N annual electricity weights (`SynergridRLPStore`)
- Add a parallel RLP-weighted monthly average property to `NordpoolBeStore`
- Expose it as a new `electricity_spot_average_price_rlp` sensor
- Add a supplier config entry type with a catalog and 4 sensors per supplier (Mega first)

**Non-Goals:**
- Changing or deprecating `electricity_spot_average_price` (unweighted, stays valid)
- Proxy sensors / `select.electricity_current_supplier` (Phase 2)
- Gas supplier support
- Any migration of existing config entries

## Decisions

### D1 — `SynergridRLPStore` is a separate class in `rlp_store.py`

The RLP data is conceptually independent from Nord Pool prices. A separate class keeps
`nordpool_store.py` focused and makes the RLP store unit-testable in isolation.

The store is instantiated in `__init__.py`, started before `NordpoolBeStore`, and
passed by reference so `NordpoolBeStore` can call `rlp_store.get_weights(date)`.

Alternative: inline into `NordpoolBeStore` — rejected (mixes two external data sources).

### D2 — RLP data fetched once per year, stored in HA Storage

The Synergrid `.xlsb` file is ex-ante and static for the full year. The store loads from
HA Storage on startup and only re-downloads when today's date is not covered (first install
or year rollover). No scheduled re-fetch subscriptions are needed.

Parsing `.xlsb` (blocking I/O via `pyxlsb`) is delegated to
`hass.async_add_executor_job`. The file is downloaded into memory — no temp files.

Alternative: download on every restart — rejected (wastes bandwidth, Synergrid not a CDN).

### D3 — Two parallel daily buffers in `NordpoolBeStore`

`monthly_average` (existing, unweighted) keeps its own `_daily_avg_buffer: dict[date, float]`
unchanged — no migration, no risk of regression.

A second `_daily_rlp_buffer: dict[date, tuple[float, float]]` stores
`(weighted_sum, weight_sum)` tuples. At midnight `_snapshot_today()` fills both buffers.

`monthly_average_rlp` = `sum(ws) / sum(wt)` across all buffer entries plus today's live
contribution. When RLP weights are unavailable for a day the fallback is an unweighted
contribution: `weighted_sum = sum(values)`, `weight_sum = len(slots)`.

The RLP buffer is persisted under a separate HA Storage key
`krowi_energy_management_nordpool_daily_rlp_avg`.

Alternative: Replace buffer — rejected (breaks `monthly_average` and the existing
`electricity_spot_average_price` sensor).

### D4 — Supplier as a new `DOMAIN_TYPE_ELECTRICITY_SUPPLIER` config entry

The config flow menu gains an `electricity_supplier` option. Selecting it shows a
two-step form: (1) pick supplier slug from a `SelectSelector` of catalog keys; (2)
optionally override the display label.

Each supplier entry is independent — multiple suppliers can coexist. No duplicate check
by slug is enforced (users may want to track the same supplier at different contract periods).

The supplier catalog lives in `const.py` as `ELECTRICITY_SUPPLIER_CATALOG: dict[str, dict]`.
`"mega"` is the first and only entry in Phase 1.

Alternative: Sub-option on the electricity entry — rejected (breaks the one-entry-per-domain
principle and makes entities harder to remove individually).

### D5 — Supplier sensors subscribe to `SIGNAL_NORDPOOL_UPDATE`

Like existing spot sensors, supplier price sensors listen to `SIGNAL_NORDPOOL_UPDATE`.
They read `hass.data[DOMAIN]["nordpool_store"].monthly_average_rlp` directly.

When `monthly_average_rlp` is `None` the sensor returns `None` (→ `unavailable`).

### D6 — Slug embedded in unique ID and entity ID verbatim

`electricity_{slug}_import_price`, `electricity_{slug}_import_price_eur`, etc. The slug
is the catalog key (`"mega"`), making entity IDs stable and human-readable.

The user-supplied label becomes the `DeviceInfo.name` only; it does not affect IDs.

## Risks / Trade-offs

- **Synergrid site change**: The `.xlsb` URL pattern may change year to year. Since the
  constant year is embedded in the URL, only the pattern needs updating in `rlp_store.py`
  each year. Mitigation: download failure is non-fatal; integration falls back to
  unweighted monthly average.

- **`pyxlsb` dependency**: Adds a new `requirements` entry. If Synergrid ever changes
  format, the dependency may need replacing. Mitigation: isolated to `rlp_store.py`.

- **DST edge days**: Spring-forward days have 92 QH slots, fall-back days 100. The
  weighted-sum / weight-sum formula handles this naturally — no special casing needed
  as long as the weight list length matches the slot list length. Mismatch is logged as
  a warning and falls back to unweighted for that day.

- **RLP buffer starts empty**: On first install `monthly_average_rlp` equals the
  weighted average of today's live slots only (no history). It converges to the true
  monthly average over ~30 days, same as `monthly_average` today.

## Migration Plan

No migration required. All new code is purely additive:
- New file: `rlp_store.py`
- New HA Storage key: `krowi_energy_management_nordpool_daily_rlp_avg`
- `nordpool_store.py` changes add a new buffer and property without touching existing ones
- Existing config entries are unaffected; the supplier entry type is opt-in

## Open Questions

None — all design questions resolved in the exploration phase.
