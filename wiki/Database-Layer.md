# Database Layer

**Source:** `modules/db.py`, `modules/models/collection_types.py`

## Connection Management

The application uses two MongoDB databases with separate connection pools:

| Database | URI Config | Purpose |
|----------|-----------|---------|
| **Current** | `PROD_MONGO_URI` or `DEV_MONGO_URI` | All application data |
| **Admin** | `ADMIN_MONGO_URI` | API keys and usage tracking |

The active current database is selected based on the `ENVIRONMENT` variable ("dev" or "prod").

### Connection Pooling

Each database has a singleton `MongoClient` instance, created on first access:

```python
MongoClient(
    uri,
    server_api=ServerApi("1"),
    tls=True,
    tlsAllowInvalidCertificates=True,
    maxPoolSize=50,
    tz_aware=True,
    tzinfo=timezone.utc,
)
```

Key settings:
- **maxPoolSize=50** -- up to 50 concurrent connections per client
- **tz_aware=True** -- all datetimes returned from MongoDB are UTC-aware
- **TLS enabled** with certificate validation disabled (for Atlas compatibility)
- **Server API v1** -- pins to stable MongoDB wire protocol

### Collection Access

`get_collection(collection: Collection)` routes to the correct database:

```python
# Admin DB collections
Collection.API_KEYS  --> admin database
Collection.API_USAGE --> admin database

# All others --> current database
Collection.MARKET_LISTINGS  --> current database
Collection.MARKET_AVERAGES  --> current database
# ... etc
```

## Collections

### Current Database

| Collection | Enum | Description |
|-----------|------|-------------|
| `trademarket_listings` | `MARKET_LISTINGS` | Raw live trade market listings |
| `trademarket_averages` | `MARKET_AVERAGES` | Computed rolling price statistics |
| `trademarket_archive` | `MARKET_ARCHIVE` | Immutable daily price snapshots |
| `lootpool` | `LOOT` | Weekly loot pool submissions |
| `raidpool` | `RAID` | Weekly raid pool submissions |
| `gambit` | `GAMBIT` | Daily raid gambit rotations |
| `lootpool_debug_logs` | `LOOT_DEBUG` | Debug payloads near pool resets (7-day TTL) |

### Admin Database

| Collection | Enum | Description |
|-----------|------|-------------|
| `api_keys` | `API_KEYS` | API key hashes, owners, and scopes |
| `api_usage` | `API_USAGE` | Per-key request counters |

## Document Schemas

### trademarket_listings

```json
{
    "name": "Divzer",
    "rarity": "Legendary",
    "item_type": "Weapon",
    "type": "Bow",
    "tier": null,
    "unidentified": false,
    "shiny_stat": null,
    "overall_roll": 87.4,
    "stat_rolls": {"dexterity": 95.2, "speed": 88.1},
    "reroll_count": 0,
    "amount": 1,
    "listing_price": 15000,
    "icon": "bow_icon_url",
    "player_name": "SomePlayer",
    "mod_version": "1.2.0",
    "hash_code": "abc123def456",
    "timestamp": "2026-03-14T12:00:00Z"
}
```

- `hash_code` is used for deduplication (unique constraint)
- `timestamp` is server-assigned at insertion time
- `player_name` is stored but excluded from API query responses

### trademarket_averages

```json
{
    "name": "Divzer",
    "tier": null,
    "shiny": false,
    "lowest_price": 8000.0,
    "highest_price": 25000.0,
    "average_price": 14200.0,
    "average_mid_80_percent_price": 13800.0,
    "p50_price": 13500.0,
    "average_p50_ema_price": 13650.0,
    "unidentified_lowest_price": null,
    "unidentified_highest_price": null,
    "unidentified_average_price": null,
    "unidentified_average_mid_80_percent_price": null,
    "unidentified_p50_price": null,
    "unidentified_average_p50_ema_price": null,
    "total_count": 24,
    "unidentified_count": 0,
    "icon": "bow_icon_url",
    "item_type": "Weapon",
    "timestamp": "2026-03-14T12:00:00Z"
}
```

- Keyed by `(name, tier, shiny)` -- one document per unique combination
- Updated via upsert whenever new listings arrive for that item

### trademarket_archive

Same schema as `trademarket_averages`. Created nightly by the archive job with the `timestamp` set to the snapshot date.

### lootpool / raidpool

```json
{
    "year": 2026,
    "week": 11,
    "region": "Corkus",
    "timestamp": "2026-03-14T12:00:00Z",
    "type": "LOOT",
    "items": [
        {
            "name": "Divzer",
            "amount": 1,
            "rarity": "Legendary",
            "shiny": false,
            "shinyStat": null,
            "icon": "bow_icon_url",
            "itemType": "Weapon",
            "type": "Bow",
            "tier": null
        }
    ]
}
```

- Keyed by `(region, year, week)` for deduplication
- `timestamp` is server-assigned, used for staleness checks

### gambit

```json
{
    "year": 2026,
    "month": 3,
    "day": 14,
    "playerName": "SomePlayer",
    "modVersion": "1.2.0",
    "timestamp": "2026-03-14T18:30:00Z",
    "gambits": [
        { "bossName": "...", "timestamp": "..." },
        { "bossName": "...", "timestamp": "..." }
    ]
}
```

- Keyed by `(year, month, day)` -- one document per gambit day
- Maximum 4 gambits per day

### api_keys

```json
{
    "key_hash": "sha256_hex_string",
    "owner": "developer_name",
    "scopes": ["read:market", "write:market"],
    "revoked": false
}
```

### api_usage

```json
{
    "key_hash": "sha256_hex_string",
    "owner": "developer_name",
    "count": 15432
}
```

- Updated via `$inc` upserts in batches of 1000

## Indexes

### Automatic Indexes

- `lootpool_debug_logs.received_at` -- TTL index, documents auto-expire after 7 days (604800 seconds)

Created at startup by `ensure_debug_indexes()`.

### Implicit Indexes

MongoDB automatically creates `_id` indexes on all collections. The application relies on query filters rather than explicit secondary indexes for most operations.
