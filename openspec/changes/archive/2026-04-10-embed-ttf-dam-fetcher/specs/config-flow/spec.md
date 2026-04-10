## MODIFIED Requirements

### Requirement: Gas config entry data shape
A gas config entry SHALL store the following fields:

| Field | Type | Required | Default |
|---|---|---|---|
| `domain_type` | `"gas"` | Yes | — |

The `unit` and `current_price_entity` fields are removed from the gas config entry. Gas unit is always `c€/kWh` (hardcoded). The spot price is fetched internally by `TtfDamStore`.

#### Scenario: Gas entry contains only domain_type after fresh setup
- **WHEN** a user completes the gas config flow on a fresh install
- **THEN** the resulting config entry data SHALL contain only `domain_type = "gas"`
- **THEN** the entry SHALL NOT contain `unit` or `current_price_entity`

---

### Requirement: Config entry migration v2 to v3
The component SHALL implement `async_migrate_entry` in `__init__.py` (extending the existing v1→v2 migration). For config entries at `VERSION = 2`, the migration SHALL:

1. For gas entries: remove `unit` and `current_price_entity` from `entry.data` if present
2. For electricity entries: no data changes required (already clean from v2)
3. For settings entries: no data changes required
4. Set `entry.version = 3` for all types

The migration SHALL be idempotent — if the fields are already absent, no error occurs.

`VERSION` at module level SHALL be updated from `2` to `3`.

#### Scenario: v2 gas entry is migrated on load
- **WHEN** a v2 gas config entry with `unit = "€/MWh"` and `current_price_entity = "sensor.krowi_ttf_dam_30d_avg"` is loaded
- **THEN** `async_migrate_entry` SHALL strip both fields
- **THEN** the resulting entry SHALL have `version = 3` and contain only `domain_type = "gas"`

#### Scenario: v2 electricity entry passes through migration unchanged
- **WHEN** a v2 electricity config entry is loaded
- **THEN** `async_migrate_entry` SHALL set `version = 3` without modifying any data fields

#### Scenario: v2 settings entry passes through migration unchanged
- **WHEN** a v2 settings config entry is loaded
- **THEN** `async_migrate_entry` SHALL set `version = 3` without modifying any data fields

#### Scenario: v3 entries are not re-migrated
- **WHEN** a v3 config entry is loaded
- **THEN** `async_migrate_entry` SHALL NOT be called

## REMOVED Requirements

### Requirement: Gas config entry `unit` field
**Reason**: Gas unit is now hardcoded to `c€/kWh`. The unit selector step is removed from the gas config flow.
**Migration**: Handled by the v2 → v3 migration which strips the `unit` field.

### Requirement: Gas config entry `current_price_entity` field
**Reason**: The `TtfDamStore` fetches the gas price internally. No external entity configuration is needed.
**Migration**: Handled by the v2 → v3 migration which strips the `current_price_entity` field. Users who had the `krowi_ttf_dam` component installed may uninstall it if they wish — it is no longer required.
