## 1. Update spot sensor display names

- [x] 1.1 In `const.py`, update `NAMES[(UID_ELECTRICITY_SPOT_CURRENT_PRICE, LANG_EN)]` to `"Current price (EPEX SPOT)"`
- [x] 1.2 In `const.py`, update `NAMES[(UID_ELECTRICITY_SPOT_CURRENT_PRICE, LANG_NL)]` to `"Huidige prijs (EPEX SPOT)"`
- [x] 1.3 In `const.py`, update `NAMES[(UID_ELECTRICITY_SPOT_AVERAGE_PRICE, LANG_EN)]` to `"Daily average price (EPEX SPOT)"`
- [x] 1.4 In `const.py`, update `NAMES[(UID_ELECTRICITY_SPOT_AVERAGE_PRICE, LANG_NL)]` to `"Gemiddelde dagprijs (EPEX SPOT)"`
- [x] 1.5 In `const.py`, update `NAMES[(UID_GAS_SPOT_TODAY_PRICE, LANG_EN)]` to `"Daily price (TTF DAM)"`
- [x] 1.6 In `const.py`, update `NAMES[(UID_GAS_SPOT_TODAY_PRICE, LANG_NL)]` to `"Dagprijs (TTF DAM)"`
- [x] 1.7 In `const.py`, update `NAMES[(UID_GAS_SPOT_AVERAGE_PRICE, LANG_EN)]` to `"Monthly average price (TTF DAM)"`
- [x] 1.8 In `const.py`, update `NAMES[(UID_GAS_SPOT_AVERAGE_PRICE, LANG_NL)]` to `"Gemiddelde maandprijs (TTF DAM)"`

## 2. Switch gas average window to calendar month

- [x] 2.1 In `ttf_dam_store.py`, add `from dateutil.relativedelta import relativedelta` import
- [x] 2.2 In `ttf_dam_store.py`, replace `from_date = (today - timedelta(days=30)).isoformat()` with `from_date = (today - relativedelta(months=1)).isoformat()`
- [x] 2.3 In `ttf_dam_store.py`, update the `average` property docstring from "30-day average" to "rolling calendar-month average"
- [x] 2.4 In `ttf_dam_store.py`, update the class docstring to reflect the month window

## 3. Sync specs

- [ ] 3.1 Archive change to sync delta specs into `openspec/specs/electricity-spot-sensors/spec.md`
- [ ] 3.2 Archive change to sync delta specs into `openspec/specs/gas-spot-sensors/spec.md`
- [ ] 3.3 Archive change to sync delta specs into `openspec/specs/ttf-dam-store/spec.md`
