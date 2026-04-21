# Raid Pool

**Sources:** `modules/routes/api/raidpool.py`, `modules/routes/api/base_pool_blueprint.py`, `modules/services/raidpool_service.py`, `modules/services/base_pool_service.py`, `modules/repositories/raidpool_repo.py`

## Overview

The raid pool system tracks weekly raid item drops and daily gambit (boss) rotations. Raid pools reset every **Friday at 18:00 UTC** -- one hour before loot pools. Gambits reset **daily at 18:00 UTC**.

## Endpoints

### Pool Endpoints (via BasePoolBlueprint)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/raidpool/items` | `write:raidpool` + mod | Submit raid pool data |
| GET | `/api/raidpool/items` | `read:raidpool` | Processed current week items |
| GET | `/api/raidpool/current` | `read:raidpool` + mod | Raw current week data |
| GET | `/api/raidpool/all` | `read:raidpool` | Paginated all weeks |
| GET | `/api/raidpool/{year}/{week}` | `read:raidpool` | Specific week data |

### Gambit Endpoints (custom)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/raidpool/gambits` | `write:raidpool` + mod | Submit daily gambits |
| GET | `/api/raidpool/gambits/current` | `read:raidpool` | Current day's gambits |

## Pool Submission

The raid pool submission flow is identical to the loot pool (see [Loot Pool](Loot-Pool.md)) but uses:
- `Collection.RAID` instead of `Collection.LOOT`
- `reset_hour=18` for week calculation (vs 19 for loot)
- Timestamp validation against the raid reset window

## Processed View (GET /api/raidpool/items)

`raidpool_repo.fetch_raidpool()` uses a different grouping pipeline than loot pools:

### Grouping Rules

| Item Type | Group |
|-----------|-------|
| `AspectItem` | Aspects |
| `GearItem` | Gear |
| Type contains "TOME" | Tomes |
| `PowderItem`, `EmeraldItem`, `AmplifierItem` | Misc |
| Everything else | Other |

### Group Sort Order

| Priority | Group |
|----------|-------|
| 1 | Aspects |
| 2 | Tomes |
| 3 | Gear |
| 4 | Misc |
| 5 | Other |

### Item Sort Order (within groups)

Items within each group are sorted by rarity:

| Priority | Rarity |
|----------|--------|
| 1 | Mythic |
| 2 | Fabled |
| 3 | Legendary |
| 4 | Rare |
| 5 | Unique |
| 6 | Common |
| 7 | Set |
| 8 | Other |

Within the "Aspects" group, items are additionally sorted by `type` then `name`. All other groups sort by `(itemType, name, tier, amount)`.

### Output Structure

```json
[
    {
        "region": "The Canyon Colossus",
        "week": 11,
        "year": 2026,
        "timestamp": "...",
        "group_items": [
            {
                "group": "Aspects",
                "loot_items": [
                    {
                        "name": "...",
                        "type": "...",
                        "rarity": "Mythic",
                        "itemType": "AspectItem",
                        "amount": 1,
                        "shiny": false,
                        "icon": "...",
                        "tier": null
                    }
                ]
            }
        ]
    }
]
```

Note: The raid pool uses `group_items` as the outer key (vs `region_items` for loot pools).

## Gambits

Gambits are daily boss rotations in Wynncraft's raid system, resetting at 18:00 UTC each day.

### Submission Flow

```
POST /api/raidpool/gambits
    |
    v
raidpool_service.save_gambits(gambits)
    |  - Max 4 gambits per submission
    |  - Version gating per gambit
    |  - Timestamp validation (must be in current gambit day)
    v
enqueue(CollectionRequest(type=GAMBIT, items=valid_gambits))
    |
    v
Queue Worker -> raidpool_repo.save_gambits()
```

### Gambit Day Window

`get_current_gambit_day()` returns `(previous_reset, next_reset)`:

- If current time >= today's 18:00 UTC: window is [today 18:00, tomorrow 18:00)
- If current time < today's 18:00 UTC: window is [yesterday 18:00, today 18:00)

### Gambit Storage

`raidpool_repo.save_gambits()`:

1. Parse and validate each gambit's timestamp against the current gambit day window
2. Build document keyed by `(year, month, day)` of the next reset
3. Remove `playerName` and `modVersion` from individual gambit entries (stored at document level)
4. Apply the same replacement rules as pools:
   - Replace if new submission has more gambits
   - Replace if existing is stale (>1 hour) and new has >= gambits
   - Otherwise, keep existing

### Gambit Retrieval

`GET /api/raidpool/gambits/current` determines the current gambit day and queries the `gambit` collection. The `_id`, `modVersion`, and `playerName` fields are excluded from the response.
