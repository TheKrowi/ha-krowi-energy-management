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

### Requirement: Import cost sensor entities display invoice-text-minus icon
The per-tariff import cost sensors and the total import cost sensor SHALL display `mdi:invoice-text-minus` as their icon.

#### Scenario: Per-tariff import cost sensor icon
- **WHEN** `electricity_import_cost_tariff_1` or `electricity_import_cost_tariff_2` is rendered in the HA UI
- **THEN** the entity displays the `mdi:invoice-text-minus` icon

#### Scenario: Total import cost sensor icon
- **WHEN** `electricity_total_import_cost` is rendered in the HA UI
- **THEN** the entity displays the `mdi:invoice-text-minus` icon

### Requirement: Export revenue sensor entities display invoice-text-plus icon
The per-tariff export revenue sensors and the total export revenue sensor SHALL display `mdi:invoice-text-plus` as their icon.

#### Scenario: Per-tariff export revenue sensor icon
- **WHEN** `electricity_export_revenue_tariff_1` or `electricity_export_revenue_tariff_2` is rendered in the HA UI
- **THEN** the entity displays the `mdi:invoice-text-plus` icon

#### Scenario: Total export revenue sensor icon
- **WHEN** `electricity_total_export_revenue` is rendered in the HA UI
- **THEN** the entity displays the `mdi:invoice-text-plus` icon

### Requirement: Net cost and gas total cost sensor entities display invoice-text icon
The electricity net cost sensor and the gas total cost sensor SHALL display `mdi:invoice-text` as their icon.

#### Scenario: Electricity net cost sensor icon
- **WHEN** `electricity_net_cost` is rendered in the HA UI
- **THEN** the entity displays the `mdi:invoice-text` icon

#### Scenario: Gas total cost sensor icon
- **WHEN** `gas_total_cost` is rendered in the HA UI
- **THEN** the entity displays the `mdi:invoice-text` icon
