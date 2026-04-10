## Context

The integration supports three config entry types — `electricity`, `gas`, and `settings` — all under the same domain `krowi_energy_management`. When HA loads an entry, `async_setup_entry` unconditionally calls `async_forward_entry_setups(entry, PLATFORMS)` with `PLATFORMS = [Platform.NUMBER, Platform.SENSOR]`. This means the settings entry is forwarded to both platforms.

In `number.async_setup_entry`, the branching logic is:

```python
if domain_type == DOMAIN_TYPE_ELECTRICITY:
    ...  # electricity descriptors
else:
    ...  # gas descriptors  ← settings entry falls here
```

The settings entry has `domain_type = "settings"`, which is neither electricity nor gas, so it silently registers a full set of gas `NumberEntity` objects. The same structural risk exists in `sensor.async_setup_entry`.

## Goals / Non-Goals

**Goals:**
- Ensure the settings entry never forwards to any platform.
- Ensure `number.async_setup_entry` and `sensor.async_setup_entry` are explicit about which domain types they handle, with a hard no-op return for unknown types.

**Non-Goals:**
- Changing what the settings entry does (language selection remains as-is).
- Introducing a new platform or entity type for settings.
- Removing the settings entry concept.

## Decisions

### 1. Guard platform forwarding at the `__init__` level (primary fix)

**Decision:** In `async_setup_entry` and `async_unload_entry`, wrap `async_forward_entry_setups` / `async_unload_platforms` in a guard:

```python
if entry.data.get(CONF_DOMAIN_TYPE) in (DOMAIN_TYPE_ELECTRICITY, DOMAIN_TYPE_GAS):
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
```

**Why:** This is the right layer. Platforms should never receive an entry that doesn't pertain to them. Fixing it here is sufficient and stops the leak at source before any platform code runs.

**Alternatives considered:**
- Fix only in `number.py` / `sensor.py` — would work but leaves the platform-forwarding contract broken; settings entry still gets dispatched to platforms unnecessarily.

### 2. Tighten `if/elif/else: return` guards in platform setup functions (defensive fix)

**Decision:** Replace the bare `else: # gas` branch in `number.async_setup_entry` (and the equivalent in `sensor.async_setup_entry`) with explicit `if/elif` plus an early `return` for unknown types:

```python
if domain_type == DOMAIN_TYPE_ELECTRICITY:
    ...
elif domain_type == DOMAIN_TYPE_GAS:
    ...
else:
    return  # settings or unknown — no entities
```

**Why:** Belt-and-suspenders. If another entry type is ever added, it won't silently inherit gas behaviour. Makes intent explicit and self-documenting.

## Risks / Trade-offs

- **Existing phantom entities in the registry**: Users who already have the settings entry loaded will have orphaned gas entities in HA's entity registry (unique IDs matching the real gas entities). These need to be removed from the registry after the fix is deployed. HA handles this gracefully — entries with no matching entity object are cleaned up on the next restart once the platform no longer registers them. No manual action required from the user.
- **`async_unload_platforms` symmetry**: If the settings entry was previously forwarded to platforms, HA may try to unload platform entries that don't exist. The guard must be applied to both setup and unload to avoid errors. → Mitigation: apply the same domain-type guard in `async_unload_entry`.

## Migration Plan

No config entry migration needed — `domain_type` is not changing and no data is being added or removed. Deploying the fix and restarting HA is sufficient. On next load, the settings entry will not register any entities, and previously registered phantom entities will be orphaned and removed by HA automatically.
