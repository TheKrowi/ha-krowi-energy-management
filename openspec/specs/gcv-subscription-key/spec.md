### Requirement: Configurable Atrias subscription key

The Atrias GCV API subscription key is exposed as an optional field in the gas entry's options flow, pre-filled with the known public default.

#### Scenario: Default key is pre-filled on first options open

- **WHEN** the user opens the gas entry's options for the first time
- **THEN** the Atrias subscription key field is pre-filled with the known public default value

#### Scenario: Key change takes effect after options save

- **WHEN** the user changes the subscription key and saves the gas options
- **THEN** the gas entry reloads and `GcvStore` uses the new key for all subsequent API calls

#### Scenario: Existing installs continue to work

- **WHEN** the gas entry has no subscription key stored in options (pre-upgrade install)
- **THEN** `__init__.py` falls back to the default constant value and `GcvStore` behaves identically to the previous hardcoded behaviour
