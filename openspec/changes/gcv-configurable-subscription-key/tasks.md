## 1. Constants & config keys

- [ ] 1.1 Add `CONF_ATRIAS_SUBSCRIPTION_KEY = "atrias_subscription_key"` to `const.py`

## 2. Config flow

- [ ] 2.1 Import `CONF_ATRIAS_SUBSCRIPTION_KEY` and `ATRIAS_SUBSCRIPTION_KEY` in `config_flow.py`
- [ ] 2.2 Add `vol.Optional(CONF_ATRIAS_SUBSCRIPTION_KEY, default=d.get(CONF_ATRIAS_SUBSCRIPTION_KEY, ATRIAS_SUBSCRIPTION_KEY)): str` to `_gas_options_schema()`

## 3. GcvStore

- [ ] 3.1 Add `subscription_key: str` parameter to `GcvStore.async_start(hass, subscription_key)`
- [ ] 3.2 Store as `self._subscription_key` and use it in both `async_fetch_month()` fetch calls instead of `ATRIAS_SUBSCRIPTION_KEY`

## 4. Init wiring

- [ ] 4.1 In `__init__.py` gas entry block, read `subscription_key = effective.get(CONF_ATRIAS_SUBSCRIPTION_KEY, ATRIAS_SUBSCRIPTION_KEY)` and pass to `gcv_store.async_start(hass, subscription_key=subscription_key)`
- [ ] 4.2 Import `CONF_ATRIAS_SUBSCRIPTION_KEY` in `__init__.py`
