## Context

`GcvStore` fetches Atrias GCV data using a subscription key hardcoded in `const.py` (`ATRIAS_SUBSCRIPTION_KEY`). The gas config entry's options flow already handles mutable gas settings (GOS zone, gas meter entity). The entry is reloaded automatically when options change via `_async_update_listener`.

## Goals / Non-Goals

**Goals:**
- Allow the Atrias subscription key to be changed from the HA UI without a HACS update.
- Pre-fill the field with the known public default so existing users notice no change.
- Key change takes effect immediately on options save (entry reload).

**Non-Goals:**
- Masking/obscuring the key in the UI (it is a public key, not a secret).
- Making the Atrias API URL configurable.
- Validating the key against the Atrias API during config flow.

## Decisions

- **`vol.Optional` with default** — the field uses `vol.Optional(CONF_ATRIAS_SUBSCRIPTION_KEY, default=ATRIAS_SUBSCRIPTION_KEY)` so the default is always stored on first options save. This avoids the need for a runtime fallback in `__init__.py` beyond `.get(key, ATRIAS_SUBSCRIPTION_KEY)`.

- **Pass via `async_start(hass, subscription_key=...)`** — consistent with how `rlp_store.async_start(hass, dso_name=dso)` passes DSO name. The store is fully configured at start time; no mid-lifecycle mutation needed.

- **`ATRIAS_SUBSCRIPTION_KEY` constant stays in `const.py`** — it remains as the default sentinel value, imported by both `config_flow.py` and `__init__.py`. No duplication.

## Risks / Trade-offs

- If a user saves gas options without touching the key field, `vol.Optional` with an explicit default ensures the key is always written to `entry.options`, so the fallback in `__init__.py` is rarely needed in practice.
- The constant in `const.py` becomes a default reference value rather than the operative value — this is a minor conceptual shift but is clearly documented by its usage context.
