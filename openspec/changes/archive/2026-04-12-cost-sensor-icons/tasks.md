## 1. Update sensor.py icons

- [x] 1.1 Set `_attr_icon = "mdi:invoice-text-minus"` on `_ElectricityTariffCostSensor` base class (covers import cost T1 and T2)
- [x] 1.2 Override `_attr_icon = "mdi:invoice-text-plus"` on `ElectricityExportRevenueT1Sensor`
- [x] 1.3 Override `_attr_icon = "mdi:invoice-text-plus"` on `ElectricityExportRevenueT2Sensor`
- [x] 1.4 Set `_attr_icon = "mdi:invoice-text-minus"` on `ElectricityTotalImportCostSensor`
- [x] 1.5 Set `_attr_icon = "mdi:invoice-text-plus"` on `ElectricityTotalExportRevenueSensor`
- [x] 1.6 Set `_attr_icon = "mdi:invoice-text"` on `ElectricityNetCostSensor`
- [x] 1.7 Set `_attr_icon = "mdi:invoice-text"` on `GasTotalCostSensor`

## 2. Update entity-icons spec

- [x] 2.1 Append new requirements for import cost, export revenue, net cost, and gas total cost icons to `openspec/specs/entity-icons/spec.md`
