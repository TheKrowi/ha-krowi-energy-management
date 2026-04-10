## MODIFIED Requirements

### Requirement: Electricity config entry data shape
An electricity config entry SHALL store the following fields:

| Field | Type | Required | Default |
|---|---|---|---|
| `domain_type` | `"electricity"` | Yes | — |
| `export_template` | string (Jinja2) | Yes | — |

The `low_price_cutoff` field SHALL be stored in the config entry **options** (not data), so it can be changed without reconfiguring:

| Field | Type | Required | Default |
|---|---|---|---|
| `low_price_cutoff` | `float` | No | `1.0` |

The `unit`, `current_price_entity`, and `fx_rate_entity` fields are removed from the electricity config entry. `unit` is always `c€/kWh` (hardcoded). `current_price_entity` and `fx_rate_entity` are no longer applicable as the spot price is fetched internally.

#### Scenario: Electricity entry contains only the new fields after fresh setup
- **WHEN** a user completes the electricity config flow on a fresh install
- **THEN** the resulting config entry data SHALL contain exactly `domain_type` and `export_template`
- **THEN** the entry SHALL NOT contain `unit`, `current_price_entity`, or `fx_rate_entity`

#### Scenario: low_price_cutoff is stored in options with default
- **WHEN** the user does not modify `low_price_cutoff` in the options flow
- **THEN** `low_price_cutoff` SHALL default to `1.0` when read from `{**entry.data, **entry.options}`

#### Scenario: User changes low_price_cutoff via options flow
- **WHEN** the user submits the electricity options flow with `low_price_cutoff = 0.9`
- **THEN** `entry.options["low_price_cutoff"]` SHALL be `0.9`
- **THEN** the electricity entry SHALL reload so the store picks up the new cutoff

---

### Requirement: Config entry migration v1 to v2
The component SHALL implement `async_migrate_entry` in `__init__.py`. For electricity config entries at `VERSION = 1`, the migration SHALL:
1. Remove `current_price_entity` and `fx_rate_entity` from `entry.data` if present
2. Remove `unit` from `entry.data` if present
3. Set `entry.version = 2`

The migration SHALL be idempotent — if the fields are already absent, no error occurs.

#### Scenario: v1 electricity entry is migrated on load
- **WHEN** a v1 electricity config entry with `current_price_entity`, `fx_rate_entity`, and `unit` is loaded
- **THEN** `async_migrate_entry` SHALL strip those three fields
- **THEN** the resulting entry SHALL have `version = 2` and contain only `domain_type` and `export_template`

#### Scenario: v1 settings and gas entries are migrated without changes
- **WHEN** a v1 settings or gas config entry is loaded
- **THEN** `async_migrate_entry` SHALL set `version = 2` without modifying any data fields

#### Scenario: v2 entries are not re-migrated
- **WHEN** a v2 config entry is loaded
- **THEN** `async_migrate_entry` SHALL NOT be called

## REMOVED Requirements

### Requirement: Electricity config entry data shape (v1 fields)
**Reason**: `current_price_entity`, `fx_rate_entity`, and `unit` are removed from the electricity entry as the component now owns the price source directly (always `c€/kWh`, always BE region, always EUR).
**Migration**: Handled automatically by the v1→v2 config entry migration in `async_migrate_entry`. No user action required.
