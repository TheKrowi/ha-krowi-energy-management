## 1. Scaffold Component Structure

- [x] 1.1 Create directory `custom_components/krowi_energy_management/`
- [x] 1.2 Create `manifest.json` with domain, name, version, config_flow, documentation, issue_tracker, codeowners, iot_class
- [x] 1.3 Create `hacs.json` at repo root with name and render_readme
- [x] 1.4 Create `const.py` with `DOMAIN`, unit option constants, and all config key string constants

## 2. Config Flow

- [x] 2.1 Create `config_flow.py` with `KrowiEnergyManagementConfigFlow`
- [x] 2.2 Implement `async_step_user` that delegates to `async_step_menu`
- [x] 2.3 Implement `async_step_menu` using HA menu step API — menu options: `electricity`, `gas`
- [x] 2.4 In `async_step_menu` handler, check existing entries for the selected `domain_type`; abort with `already_configured` if duplicate found
- [x] 2.5 Implement `async_step_electricity` — form with `unit` selector, `current_price_entity` (default `sensor.nord_pool_be_current_price`), optional `fx_rate_entity`, `export_template`; creates entry with `domain_type = "electricity"` and title `"Electricity"`
- [x] 2.6 Implement `async_step_gas` — form with `unit` selector, `current_price_entity` (default `sensor.krowi_ttf_dam_30d_avg`); creates entry with `domain_type = "gas"` and title `"Gas"`
- [x] 2.7 Implement `OptionsFlow` that reads `entry.data["domain_type"]` and routes to `async_step_electricity_options` or `async_step_gas_options`
- [x] 2.8 `async_step_electricity_options` — pre-populate all current electricity entry values; save triggers entry reload
- [x] 2.9 `async_step_gas_options` — pre-populate all current gas entry values; save triggers entry reload
- [ ] 2.10 Verify options flow reload affects only the saved entry, not sibling entries
- [x] 2.11 In `async_setup_entry`, delete any existing Repairs issue for this entry (`ir.async_delete_issue`) before registering the registry listener
- [x] 2.12 Register an `EVENT_ENTITY_REGISTRY_UPDATED` listener in `async_setup_entry`; on `action == "update"` with `"entity_id"` in changed keys and entity belonging to this entry, call `ir.async_create_issue` with `severity=IssueSeverity.WARNING` and `issue_id=f"entity_renamed_{entry_id}"`
- [x] 2.13 In `async_unload_entry`, unsubscribe the registry listener and delete the Repairs issue
- [x] 2.14 Add `entity_renamed` translation key to `strings.json` and `translations/en.json` for the Repairs issue title and description

## 3. Strings & Translations

- [x] 3.1 Create `strings.json` with config flow step labels, field descriptions, and all entity friendly names
- [x] 3.2 Create `translations/en.json` mirroring `strings.json`

## 4. Unit Conversion Helper

- [x] 4.1 Implement `_convert_unit(value: float, from_unit: str, to_unit: str) -> float | None` in a shared location (e.g. `utils.py` or inline in sensors)
- [x] 4.2 Support conversions: kWh↔MWh↔Wh and their c€ prefixed equivalents
- [x] 4.3 Return `None` and log a warning when `from_unit` is unrecognised
- [x] 4.4 Apply FX multiplier: if `fx_rate_entity` is set, multiply converted value by state of that entity; return `None` if FX entity unavailable or non-numeric

## 5. Number Entities

- [x] 5.1 Create `number.py` with `KrowiNumberEntity(NumberEntity, RestoreNumber)`
- [x] 5.2 Implement `async_setup_entry` to create all 10 number entities from a descriptor list
- [x] 5.3 Add 5 electricity number entity descriptors (see electricity-tariff-entities spec for IDs, names, units, step, min, max)
- [x] 5.4 Add 5 gas number entity descriptors (see gas-tariff-entities spec)
- [x] 5.5 Set VAT entities to `unit = "%"`, `step = 0.01`, `min = 0`, `max = 100`
- [x] 5.6 Set all rate entities to `unit = electricity_unit / gas_unit`, `step = 0.00001`, `min = 0`, `max = 9999`
- [x] 5.7 Set `mode = NumberMode.BOX` on all number entities
- [x] 5.8 Implement `async_added_to_hass` with restore logic; set initial value to `0` if no restore state found
- [x] 5.9 Implement `async_set_native_value` to update and persist the value
- [x] 5.10 Return `DeviceInfo` from all electricity number entities: identifier `(DOMAIN, f"{entry_id}_electricity")`, name `"Electricity"`
- [x] 5.11 Return `DeviceInfo` from all gas number entities: identifier `(DOMAIN, f"{entry_id}_gas")`, name `"Gas"`

## 6. Base Sensor Infrastructure

- [x] 6.1 Create `sensor.py` and implement `async_setup_entry` that creates all 6 sensor entities
- [x] 6.2 Implement a base `KrowiSensor(SensorEntity)` with common attributes
- [x] 6.3 Add `async_added_to_hass` / `async_will_remove_from_hass` lifecycle hooks for state-change listeners
- [x] 6.4 Add helper to safely read a number entity's float state from `hass.states.get(entity_id)`, returning `None` when unavailable/unknown
- [x] 6.5 Return `DeviceInfo` from all electricity sensors: identifier `(DOMAIN, f"{entry_id}_electricity")`, name `"Electricity"`
- [x] 6.6 Return `DeviceInfo` from all gas sensors: identifier `(DOMAIN, f"{entry_id}_gas")`, name `"Gas"`

## 7. Electricity Surcharge Sensors

- [x] 7.1 Implement `ElectricityTotalSurchargeSensor` — sums 4 electricity rate entities; unit=electricity_unit; state_class=measurement; round=5
- [x] 7.2 Register `async_track_state_change_event` for all 4 contributing rate entities
- [x] 7.3 Implement `ElectricitySurchargeFormulaSensor` — renders `"<r1> + <r2> + <r3> + <r4> = <total>"` string; no unit or state_class
- [x] 7.4 Register state-change listeners for the same 4 rate entities in the formula sensor

## 8. Electricity Import Price Sensor

- [x] 8.1 Implement `ElectricityImportPriceSensor` — formula: `(nord_pool_current_converted + surcharge) * (1 + vat / 100)`; round=5
- [x] 8.2 Register `async_track_state_change_event` for: Nord Pool current entity, FX entity (if set), own surcharge sensor, own VAT number entity
- [x] 8.3 On each update: read Nord Pool state, get its `unit_of_measurement`, call unit conversion helper; set sensor unavailable if conversion returns `None`
- [x] 8.4 Apply FX: if `fx_rate_entity` set, multiply converted Nord Pool value by FX sensor state; set unavailable if FX entity missing/non-numeric

## 9. Electricity Export Price Sensor

- [x] 9.1 Implement `ElectricityExportPriceSensor` using `async_track_template_result`
- [x] 9.2 On template render result callback: set state to rendered float string; set unavailable on template error and log the error
- [x] 9.3 Cancel template subscription in `async_will_remove_from_hass`

## 10. Gas Surcharge Sensor

- [x] 10.1 Implement `GasTotalSurchargeSensor` — sums 4 gas rate entities; unit=gas_unit; state_class=measurement; round=5
- [x] 10.2 Register `async_track_state_change_event` for all 4 contributing gas rate entities

## 11. Gas Current Price Sensor

- [x] 11.1 Implement `GasCurrentPriceSensor` — formula: `(ttf_dam_converted + surcharge) * (1 + vat / 100)`; round=5
- [x] 11.2 Register `async_track_state_change_event` for: TTF DAM entity, own gas surcharge sensor, own gas VAT number entity
- [x] 11.3 On each update: read TTF DAM state, get its `unit_of_measurement`, call unit conversion helper to convert to gas_unit; set sensor unavailable if conversion returns `None`

## 12. Component Entry Point

- [x] 12.1 Create `__init__.py` with `async_setup_entry` that reads `entry.data["domain_type"]` and forwards to the appropriate platforms (`number`, `sensor`)
- [x] 12.2 Create `async_unload_entry` that unloads the platforms for the given entry
- [ ] 12.3 Verify electricity and gas entries load and unload independently

## 13. Manual Verification

- [ ] 13.1 Install via HACS custom repository; confirm all 16 entities appear in HA
- [ ] 13.2 Set electricity VAT to 21%, gas VAT to 6%, and several rates; verify surcharge formula string updates correctly
- [ ] 13.3 Verify electricity import price recomputes when Nord Pool entity state changes
- [ ] 13.4 Verify export price sensor re-renders when entities referenced in the template change
- [ ] 13.5 Verify gas current price recomputes when TTF DAM entity state changes
- [ ] 13.6 Verify all computed sensors go `unavailable` when Nord Pool / TTF DAM entity is removed
- [ ] 13.7 Restart HA; verify all number entity values are restored from `RestoreNumber`
- [ ] 13.8 Change `electricity_unit` via options flow; verify options flow triggers reload and entities show new unit
