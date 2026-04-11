## Context

All entity classes in `number.py` and `sensor.py` currently have no `_attr_icon` defined, so HA renders a generic default icon for every entity. With 21 distinct entities across two energy domains, the absence of icons makes dashboards hard to scan at a glance.

## Goals / Non-Goals

**Goals:**
- All number and sensor entity classes have a meaningful `_attr_icon` class attribute
- Icon vocabulary distinguishes tariff inputs (`mdi:cash-edit`), VAT (`mdi:percent`), computed surcharges (`mdi:cash-lock`), formula readouts (`mdi:function-variant`), and price sensors (`mdi:currency-eur`)

**Non-Goals:**
- Dynamic icons (icon changing based on state)
- Custom icon overrides in config/options flow
- Icons for config flow steps or the integration entry itself

## Decisions

### Decision 1: Use `_attr_icon` class attribute (not `icon_template` or `@property`)

`_attr_icon` is the idiomatic HA pattern for a static icon. It is a plain class-level string — zero runtime overhead, no property call, no template rendering. Alternative `icon` property is only needed when icons must change dynamically, which is not the case here.

### Decision 2: Icon vocabulary maps to entity role, not energy type

Rather than using energy-type icons (`mdi:lightning-bolt`, `mdi:fire`), icons map to the entity's functional role:
- `mdi:cash-edit` — editable tariff rate inputs (the rates you enter/adjust)
- `mdi:percent` — VAT rates (dimensionally different from currency rates)
- `mdi:cash-lock` — computed surcharge totals (regulatory, not user-editable)
- `mdi:function-variant` — formula string sensors (they display an equation)
- `mdi:currency-eur` — all price sensors (market prices and all-in prices)

Energy-type icons (`mdi:lightning-bolt`, `mdi:fire`, `mdi:gas-burner`) semantically belong to consumed-energy entities (kWh, W), not cost-per-energy sensors.

### Decision 3: Import/export price sensors use `mdi:currency-eur`, not directional icons

`mdi:home-import-outline` / `mdi:home-export-outline` were considered, but rejected: these icons are already widely used in HA for energy consumption/production sensors. Using them for price sensors would create visual confusion with the energy dashboard. `mdi:currency-eur` is unambiguous.

### Decision 4: Each subclass gets its own `_attr_icon`, not the base class

`KrowiSensor` and `KrowiNumberEntity` are base classes shared by entities with different roles. A single base-class icon would be overridden by subclasses anyway, so setting it on the base would add noise without benefit. Each concrete subclass declares its own icon.

## Risks / Trade-offs

- [Risk] MDI icon names may be deprecated in future Material Design releases → Mitigation: all chosen icons (`cash-edit`, `cash-lock`, `percent`, `function-variant`, `currency-eur`) are stable, widely used HA icons with no deprecation history
- [Risk] `mdi:cash-edit` and `mdi:cash-lock` are visually similar → Mitigation: the lock glyph is distinct enough; users who hover see the entity name which disambiguates
