## Why

HA generates `entity_id` by slugifying `_attr_name` at registration time, making entity IDs dependent on the display name's word order and language. This breaks the stable English identifier scheme established by `UID_*` constants in `const.py` — for example, `UID_ELECTRICITY_PRICE_IMPORT = "electricity_price_import"` currently produces `sensor.electricity_import_price` because the entity name is "Electricity import price".

## What Changes

- Explicitly set `self.entity_id` in every sensor entity's `__init__` in `sensor.py` using `f"sensor.{uid}"` with the corresponding `UID_*` constant.
- Explicitly set `self.entity_id` in `KrowiNumberEntity.__init__` in `number.py` using `f"number.{descriptor.unique_id_suffix}"`.
- `_attr_name` becomes purely a display label — Dutch or any language can be used freely without affecting entity IDs.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None — this is a pure implementation fix. No spec-level requirements change; specs do not define entity ID formats.

## Impact

- `sensor.py`: 8 sensor classes each gain one `self.entity_id` assignment in `__init__`
- `number.py`: `KrowiNumberEntity.__init__` gains one `self.entity_id` assignment (covers all number entities via the shared base class)
- **Existing dev installs**: entity registry must be cleared (remove + re-add integration) after deploying this change
