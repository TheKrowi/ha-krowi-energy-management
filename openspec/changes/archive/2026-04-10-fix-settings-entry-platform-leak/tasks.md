## 1. Guard platform forwarding in __init__.py

- [x] 1.1 In `async_setup_entry`, wrap `async_forward_entry_setups(entry, PLATFORMS)` in a guard: only forward if `domain_type` is `DOMAIN_TYPE_ELECTRICITY` or `DOMAIN_TYPE_GAS`
- [x] 1.2 In `async_unload_entry`, wrap `async_unload_platforms(entry, PLATFORMS)` in the same guard so unload is symmetric with setup

## 2. Tighten number platform guard

- [x] 2.1 In `number.async_setup_entry`, replace the bare `else:` (gas) branch with `elif domain_type == DOMAIN_TYPE_GAS:` followed by an `else: return` for unknown types

## 3. Tighten sensor platform guard

- [x] 3.1 In `sensor.async_setup_entry`, locate the equivalent `if electricity / else gas` branching and replace with explicit `if/elif/else: return`
