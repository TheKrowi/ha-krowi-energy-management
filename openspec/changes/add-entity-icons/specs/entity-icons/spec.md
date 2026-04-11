## ADDED Requirements

### Requirement: Tariff rate number entities display cash-edit icon
All electricity and gas tariff rate number entities (green energy contribution, distribution & transport, excise duty, energy contribution for both domains) SHALL display `mdi:cash-edit` as their icon.

#### Scenario: Electricity tariff rate entity icon
- **WHEN** an electricity tariff rate number entity is rendered in the HA UI
- **THEN** the entity displays the `mdi:cash-edit` icon

#### Scenario: Gas tariff rate entity icon
- **WHEN** a gas tariff rate number entity is rendered in the HA UI
- **THEN** the entity displays the `mdi:cash-edit` icon

### Requirement: VAT number entities display percent icon
The VAT number entities for electricity and gas SHALL display `mdi:percent` as their icon.

#### Scenario: VAT entity icon
- **WHEN** a VAT number entity (electricity or gas) is rendered in the HA UI
- **THEN** the entity displays the `mdi:percent` icon

### Requirement: Surcharge sensor entities display cash-lock icon
The total surcharge sensor entities for electricity and gas SHALL display `mdi:cash-lock` as their icon.

#### Scenario: Surcharge sensor icon
- **WHEN** a total surcharge sensor entity is rendered in the HA UI
- **THEN** the entity displays the `mdi:cash-lock` icon

### Requirement: Surcharge formula sensor entities display function-variant icon
The total surcharge formula sensor entities for electricity and gas SHALL display `mdi:function-variant` as their icon.

#### Scenario: Surcharge formula sensor icon
- **WHEN** a surcharge formula sensor entity is rendered in the HA UI
- **THEN** the entity displays the `mdi:function-variant` icon

### Requirement: Price sensor entities display currency-eur icon
All price sensor entities (spot current/average, import/export prices, EUR bridge sensors, gas current price, gas spot prices) SHALL display `mdi:currency-eur` as their icon.

#### Scenario: Electricity spot price sensor icon
- **WHEN** an electricity spot current or average price sensor is rendered in the HA UI
- **THEN** the entity displays the `mdi:currency-eur` icon

#### Scenario: Electricity all-in price sensor icon
- **WHEN** an electricity import or export price sensor (c€/kWh or EUR/kWh) is rendered in the HA UI
- **THEN** the entity displays the `mdi:currency-eur` icon

#### Scenario: Gas price sensor icon
- **WHEN** a gas spot, current price, or EUR bridge sensor is rendered in the HA UI
- **THEN** the entity displays the `mdi:currency-eur` icon
