# Spec: consistent-entity-ids

## Purpose

Defines the canonical naming convention and UID table for all entities in the `krowi_energy_management` integration.

## Requirements

### Requirement: Entity UIDs follow a structured grouping scheme
All entity unique IDs SHALL follow a consistent naming convention using infixes to group entities semantically.

| Group | Infix | Applies to |
|-------|-------|------------|
| Tariff inputs | `_tariff_` | User-editable rate number entities |
| Derived tariff sum | `_tariff_total_` | Sum sensors derived from tariff inputs |
| Price outputs | `_current_price_` | Computed spot price sensors |
| VAT | _(none)_ | VAT number entities — VAT applies to total price, not a tariff component |

#### Scenario: Tariff input entities use _tariff_ infix
- **WHEN** any electricity or gas tariff rate number entity is registered in HA
- **THEN** its unique ID SHALL contain `_tariff_` as a structural infix (e.g. `electricity_tariff_excise_duty`)

#### Scenario: VAT entities have no infix
- **WHEN** the electricity or gas VAT number entity is registered in HA
- **THEN** its unique ID SHALL be `electricity_vat` or `gas_vat` respectively — no `_tariff_` infix

#### Scenario: Price output sensors use _current_price_ infix
- **WHEN** any electricity or gas price sensor is registered in HA
- **THEN** its unique ID SHALL contain `_current_price_` as a structural infix

---

### Requirement: Canonical UID table
The following unique IDs SHALL be used for all entities. No other UID values are valid.

**Electricity number entities:**

| Unique ID | Friendly name (EN) | Friendly name (NL) |
|-----------|-------------------|-------------------|
| `electricity_tariff_green_energy_contribution` | Green energy contribution | Groene stroom bijdrage |
| `electricity_tariff_distribution_transport` | Distribution & transport | Distributie & transport |
| `electricity_tariff_excise_duty` | Excise duty | Bijzondere accijns |
| `electricity_tariff_energy_contribution` | Energy contribution | Energiebijdrage |
| `electricity_vat` | VAT | BTW |

**Gas number entities:**

| Unique ID | Friendly name (EN) | Friendly name (NL) |
|-----------|-------------------|-------------------|
| `gas_tariff_distribution` | Distribution | Distributie |
| `gas_tariff_transport` | Transport (Fluxys) | Transport (Fluxys) |
| `gas_tariff_excise_duty` | Excise duty | Bijzondere accijns |
| `gas_tariff_energy_contribution` | Energy contribution | Energiebijdrage |
| `gas_vat` | VAT | BTW |

**Electricity sensor entities:**

| Unique ID | Friendly name (EN) | Friendly name (NL) |
|-----------|-------------------|-------------------|
| `electricity_tariff_total_surcharge` | Total surcharge | Totale toeslag |
| `electricity_tariff_total_surcharge_formula` | Total surcharge formula | Totale toeslag formule |
| `electricity_current_price_import` | Current import price | Actuele importprijs |
| `electricity_current_price_export` | Current export price | Actuele exportprijs |
| `electricity_current_price_import_eur` | Current import price (EUR/kWh) | Actuele importprijs (EUR/kWh) |
| `electricity_current_price_export_eur` | Current export price (EUR/kWh) | Actuele exportprijs (EUR/kWh) |

**Gas sensor entities:**

| Unique ID | Friendly name (EN) | Friendly name (NL) |
|-----------|-------------------|-------------------|
| `gas_tariff_total_surcharge` | Total surcharge | Totale toeslag |
| `gas_tariff_total_surcharge_formula` | Total surcharge formula | Totale toeslag formule |
| `gas_current_price` | Current price | Actuele prijs |
| `gas_current_price_eur` | Current price (EUR/kWh) | Actuele prijs (EUR/kWh) |

#### Scenario: All entities registered with correct UIDs
- **WHEN** the integration is loaded with both electricity and gas entries
- **THEN** all 20 entities SHALL be present in the HA entity registry with exactly the UIDs listed in the table above
