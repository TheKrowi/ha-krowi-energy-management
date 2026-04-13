## MODIFIED Requirements

### Requirement: Store exposes derived attributes
The store SHALL expose the following computed properties (updated table, new row added):

| Property | Type | Description |
|---|---|---|
| `current_price` | `float \| None` | Value of the currently active 15-min slot |
| `average` | `float \| None` | Mean of all `value` entries in `data_today` (using `statistics.mean`), rounded to 5 dp |
| `monthly_average` | `float \| None` | `mean([*_daily_avg_buffer.values(), average])` rounded to 5 dp; `None` if `average` is `None` |
| `monthly_average_rlp` | `float \| None` | RLP-weighted mean of all 15-min slots in the rolling calendar-month window; `None` if `average` is `None`. Falls back to unweighted when RLP weights unavailable for a day |
| `low_price` | `bool \| None` | `True` if `current_price < average * low_price_cutoff`; `None` if either is `None` |
| `price_percent_to_average` | `float \| None` | `current_price / average` rounded to 5 decimal places; `None` if either is `None` |
| `today` | `list[float]` | All 96 `value` entries in chronological order |
| `tomorrow` | `list[float]` | All 96 `value` entries for tomorrow, or `[]` if not yet available |
| `tomorrow_valid` | `bool` | `True` if `data_tomorrow` contains a full 96-slot dataset |

#### Scenario: Average computed from 96 slots
- **WHEN** `data_today` contains 96 slots with values
- **THEN** `store.average` SHALL equal `statistics.mean(slot["value"] for slot in data_today)` rounded to 5 decimal places

#### Scenario: RLP-weighted monthly average with full buffer
- **WHEN** `_daily_rlp_buffer` has 30 entries (each a `(weighted_sum, weight_sum)` tuple) and today's RLP-weighted contribution is available
- **THEN** `store.monthly_average_rlp` SHALL equal `round(sum(ws) / sum(wt), 5)` across all buffer entries plus today's live contribution

#### Scenario: RLP monthly average with unweighted fallback day
- **WHEN** `SynergridRLPStore` does not have weights for one day in the window
- **THEN** that day's contribution SHALL use `weight_sum = len(slots)` and `weighted_sum = sum(slot["value"] for slot in slots)`

#### Scenario: Monthly average with full buffer
- **WHEN** `_daily_avg_buffer` has 30 entries and `self.average = 9.50000`
- **THEN** `store.monthly_average` SHALL equal `round(mean([*buffer_values, 9.50000]), 5)`

#### Scenario: Monthly average when store has no data
- **WHEN** `self.average` is `None`
- **THEN** `store.monthly_average` SHALL be `None`
- **THEN** `store.monthly_average_rlp` SHALL be `None`

#### Scenario: Low price flag when price is below cutoff
- **WHEN** `current_price = 7.5`, `average = 10.0`, `low_price_cutoff = 1.0`
- **THEN** `store.low_price` SHALL be `True`

#### Scenario: Low price flag when price is above cutoff
- **WHEN** `current_price = 12.0`, `average = 10.0`, `low_price_cutoff = 1.0`
- **THEN** `store.low_price` SHALL be `False`

---

## ADDED Requirements

### Requirement: Store maintains a second RLP-weighted monthly average
The `NordpoolBeStore` SHALL maintain a second buffer `_daily_rlp_buffer: dict[date, tuple[float, float]]`
alongside the existing unweighted `_daily_avg_buffer: dict[date, float]`. The two buffers are
independent. The existing `monthly_average` and `_daily_avg_buffer` are **unchanged**.

The store SHALL accept a `SynergridRLPStore` reference in `async_start()`.

**RLP buffer format:** `dict[date, tuple[float, float]]`
- `weighted_sum` = `sum(slot["value"] × rlp_weight[i] for i, slot in enumerate(slots))`
- `weight_sum` = `sum(rlp_weight[i] for i in range(len(slots)))`
- Fallback when RLP weights unavailable: `weighted_sum = sum(values)`, `weight_sum = len(slots)`

`monthly_average_rlp` = `sum(ws) / sum(wt)` across `_daily_rlp_buffer.values()` + today's live contribution.

The RLP buffer SHALL be persisted under HA Storage key `krowi_energy_management_nordpool_daily_rlp_avg`.

#### Scenario: Midnight snapshot writes to both buffers
- **WHEN** the clock reaches 00:00:01
- **THEN** `_snapshot_today()` SHALL write the unweighted average to `_daily_avg_buffer` (unchanged)
- **THEN** `_snapshot_today()` SHALL also write `(weighted_sum, weight_sum)` to `_daily_rlp_buffer`
- **THEN** if RLP weights are unavailable for yesterday, the RLP entry SHALL use the unweighted fallback

#### Scenario: monthly_average unchanged
- **WHEN** `_daily_avg_buffer` has 30 float entries and `self.average = 9.50000`
- **THEN** `store.monthly_average` SHALL equal `round(mean([*buffer_values, 9.50000]), 5)` (identical to pre-RLP behaviour)
