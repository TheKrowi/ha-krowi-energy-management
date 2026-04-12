## ADDED Requirements

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
