## 1. number.py — pin entity IDs

- [x] 1.1 In `KrowiNumberEntity.__init__`, add `self.entity_id = f"number.{descriptor.unique_id_suffix}"` after the `self._attr_unique_id` assignment

## 2. sensor.py — pin entity IDs for electricity sensors

- [x] 2.1 In `ElectricitySurchargeSensor.__init__`, add `self.entity_id = f"sensor.{UID_ELECTRICITY_SURCHARGE_RATE}"`
- [x] 2.2 In `ElectricitySurchargeFormulaSensor.__init__`, add `self.entity_id = f"sensor.{UID_ELECTRICITY_SURCHARGE_FORMULA}"`
- [x] 2.3 In `ElectricityImportPriceSensor.__init__`, add `self.entity_id = f"sensor.{UID_ELECTRICITY_PRICE_IMPORT}"`
- [x] 2.4 In `ElectricityExportPriceSensor.__init__`, add `self.entity_id = f"sensor.{UID_ELECTRICITY_PRICE_EXPORT}"`
- [x] 2.5 In `ElectricityImportPriceEurSensor.__init__`, add `self.entity_id = f"sensor.{UID_ELECTRICITY_PRICE_IMPORT_EUR}"`
- [x] 2.6 In `ElectricityExportPriceEurSensor.__init__`, add `self.entity_id = f"sensor.{UID_ELECTRICITY_PRICE_EXPORT_EUR}"`

## 3. sensor.py — pin entity IDs for gas sensors

- [x] 3.1 In `GasSurchargeSensor.__init__`, add `self.entity_id = f"sensor.{UID_GAS_SURCHARGE_RATE}"`
- [x] 3.2 In `GasCurrentPriceSensor.__init__`, add `self.entity_id = f"sensor.{UID_GAS_PRICE}"`

## 4. Verify

- [ ] 4.1 Remove both config entries in HA (electricity + gas) to clear old entity registry entries
- [ ] 4.2 Re-add both config entries and confirm entity IDs match the UID constants (e.g. `sensor.electricity_price_import`, `number.electricity_vat_rate`)
