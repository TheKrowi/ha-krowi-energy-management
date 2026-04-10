## Context

HA's entity platform assigns `entity_id` by slugifying the entity's `name` at first registration and storing it in the entity registry keyed by `unique_id`. Subsequent restarts reuse the stored value, so the initial name drives the permanent ID unless the user manually renames it.

The `UID_*` constants in `const.py` define a deliberate English naming scheme for all entities. Currently nothing enforces that `entity_id` matches these constants — any rename of `_attr_name` (e.g. to Dutch) would silently produce Dutch entity IDs on fresh installs.

## Goals / Non-Goals

**Goals:**
- `entity_id` for every sensor and number entity is deterministically derived from the corresponding `UID_*` constant, regardless of `_attr_name`.
- `_attr_name` (the display label) is fully decoupled from the entity ID.

**Non-Goals:**
- Migration of existing installs with old entity IDs — this is dev-stage only; re-adding the integration is sufficient.
- Changing the `UID_*` values themselves.
- Changing any display names in this change.

## Decisions

### Explicit `self.entity_id` assignment in `__init__`

Set `self.entity_id = f"sensor.{uid}"` (or `f"number.{uid}"`) directly inside each entity's `__init__`. HA honours an explicitly set `entity_id` over its auto-generated slug.

**Why this over alternatives:**
- **`translation_key` approach**: More HA-idiomatic long-term, but requires translation files, `_attr_has_entity_name = True`, and significant refactor. Disproportionate for this fix.
- **Renaming `_attr_name` to match word order**: Would force English names in a specific word order (awkward), and still wouldn't prevent drift if names change later.
- **Explicit assignment**: One line per entity, zero indirection, immediately auditable. Entity IDs are colocated with the constant they reference.

### Single change point for number entities

`KrowiNumberEntity.__init__` sets `self.entity_id = f"number.{descriptor.unique_id_suffix}"`. All number entities share this base class — one fix covers all ten number entities.

### Sensor entities each set their own `entity_id`

Sensors don't share a single `__init__` path (each class builds differently), so each of the 8 sensor classes adds its own line. This keeps sensor construction explicit.

## Risks / Trade-offs

- **Fresh-install only guarantee**: The fix ensures correct entity IDs on new registrations. Existing registrations with old IDs persist in `.storage/core.entity_registry` — user must remove and re-add the integration.  
  → Mitigation: Documented in the proposal. Acceptable in dev stage.
- **No compile-time enforcement**: Nothing prevents a future entity from omitting `self.entity_id`. A code review checklist or comment in `__init__` pattern can catch this.
  → Mitigation: Tasks will include a reminder comment in the base class.
