# Time Validation

**Source:** `modules/utils/time_validation.py`

## Overview

Time validation is critical to the WynnVentory backend because Wynncraft game events operate on strict UTC-based reset schedules. The system must correctly determine which week/day a submission belongs to, reject stale data, and identify reset windows.

## Reset Schedules

| Event | Reset Day | Reset Time (UTC) | Period |
|-------|-----------|-------------------|--------|
| **Raid pool** | Friday | 18:00 | Weekly |
| **Loot pool** | Friday | 19:00 | Weekly |
| **Gambits** | Daily | 18:00 | Daily |

Note that raid and loot pools reset on the same day but at different hours. This one-hour difference is important for correctly assigning submissions to weeks.

## Timestamp Parsing

### parse_utc_timestamp(value)

Strict ISO-8601 UTC timestamp parser. **All timestamps in the system must be timezone-aware.**

Accepted formats:
- `"2026-01-04T14:22:33Z"` -- Zulu suffix
- `"2026-01-04T14:22:33.179345200Z"` -- with fractional seconds
- `"2026-01-04T14:22:33+00:00"` -- explicit UTC offset
- Timezone-aware `datetime` objects

Rejected:
- Naive datetimes (no timezone info) -- raises `ValueError`
- Legacy format `"YYYY-MM-DD HH:MM:SS"` (no T separator) -- raises `ValueError`
- Non-UTC-format strings without timezone indicator

Processing:
1. Normalize `Z` suffix to `+00:00`
2. Strip fractional seconds (precision is seconds only)
3. Parse via `datetime.fromisoformat()`
4. Convert to UTC, truncate microseconds

## Week Calculation

### get_lootpool_week() / get_raidpool_week()

Returns `(year, week)` tuple for the current moment using ISO week numbering.

### get_lootpool_week_for_timestamp(timestamp, reset_day=4, reset_hour)

Computes which Wynncraft week a given timestamp falls into:

```
1. Parse timestamp to UTC datetime
2. Find the most recent reset day (Friday = weekday 4)
3. If today IS the reset day but BEFORE reset hour:
   --> Use the previous week's reset as the anchor
4. Compute last_reset = anchor at reset_hour
5. Compute next_reset = last_reset + 7 days
6. If timestamp >= next_reset: return next_reset's ISO week/year
7. Otherwise: return last_reset's ISO week/year
```

Example (with loot reset at 19:00 UTC):
- Friday 18:59 UTC -> belongs to the previous week (hasn't reset yet)
- Friday 19:01 UTC -> belongs to the new week

## Gambit Day Calculation

### get_current_gambit_day(now=None)

Returns `(previous_reset, next_reset)` as UTC datetimes:

```
reset_hour = 18:00 UTC

If now >= today's 18:00:
    previous = today 18:00
    next     = tomorrow 18:00
Else:
    previous = yesterday 18:00
    next     = today 18:00
```

## Week Range

### get_week_range(reset_day, reset_hour, now=None)

Returns `(last_reset, next_reset)` as UTC datetimes for any pool type:

1. Find the most recent occurrence of `reset_day`
2. Set time to `reset_hour:00:00`
3. If today is reset day but before reset time, subtract 7 days
4. `next_reset = last_reset + 7 days`

## Time Validation Functions

### is_time_valid(pool_type, time_value)

Validates that a timestamp falls within the current period for a given pool type:

| Pool Type | Valid Window |
|-----------|-------------|
| `RAID` | `[last_raid_reset, next_raid_reset)` |
| `LOOT` | `[last_loot_reset, next_loot_reset)` |
| `GAMBIT` | `[previous_gambit_reset, next_gambit_reset)` |

Used during submission to reject items with timestamps from previous weeks/days.

### is_in_reset_window(pool_type, margin_minutes=10)

Returns `True` if the current time is within `margin_minutes` before or after the next reset. Used to trigger debug payload logging near reset boundaries.

```
[next_reset - 10min, next_reset + 10min]
```

## Constants

```python
raid_reset_hour = 18   # 6 PM UTC
loot_reset_hour = 19   # 7 PM UTC
reset_day = 4          # Friday (Python weekday: Monday=0)
```
