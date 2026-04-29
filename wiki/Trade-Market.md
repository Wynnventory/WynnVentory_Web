# Trade Market

**Sources:** `modules/routes/api/market.py`, `modules/services/market_service.py`, `modules/repositories/market_repo.py`

## Overview

The trade market system handles the ingestion, storage, statistical computation, and retrieval of Wynncraft in-game trade market listings. It is the most complex domain in the backend, involving three MongoDB collections and a multi-stage price computation pipeline.

## Data Flow

```
Game Mod (POST /api/trademarket/items)
    |
    v
market_service.save_items()
    |  - Version gating
    |  - Field mapping (camelCase -> snake_case)
    v
Queue Worker
    |
    v
market_repo.save()
    |  - Insert into MARKET_LISTINGS (dedup by hash_code)
    |  - Trigger update_moving_averages()
    v
MARKET_AVERAGES  (live rolling statistics)
    |
    | (nightly archive job)
    v
MARKET_ARCHIVE   (immutable daily snapshots)
```

## Listing Ingestion

### Field Mapping

The service layer maps incoming camelCase fields to snake_case for storage:

| Incoming Field | Stored Field |
|---------------|-------------|
| `item.name` | `name` |
| `item.rarity` | `rarity` |
| `item.itemType` | `item_type` |
| `item.type` | `type` |
| `item.tier` | `tier` |
| `item.unidentified` | `unidentified` |
| `item.shinyStat` | `shiny_stat` |
| `item.overallRollPercentage` | `overall_roll` |
| `item.actualStatsWithPercentage` | `stat_rolls` |
| `item.rerollCount` | `reroll_count` |
| `amount` | `amount` |
| `listingPrice` | `listing_price` |
| `playerName` | `player_name` |
| `modVersion` | `mod_version` |
| `hash_code` | `hash_code` |

### Version Gating

Each listing's `modVersion` is checked against `Config.MIN_SUPPORTED_VERSION` using the version comparator. Listings from outdated mod versions are silently dropped.

### Deduplication

`market_repo.save()` uses `insert_many(ordered=False)`. If any `hash_code` already exists, that document fails to insert but all others succeed. The `BulkWriteError` is caught and the number of successful inserts is extracted from `bwe.details["nInserted"]`.

## Price Statistics Computation

### Trigger

After successful inserts, `update_moving_averages()` is called with the inserted items. This uses a `ThreadPoolExecutor` for parallel processing -- each unique `(name, tier, shiny)` combination is processed in its own thread.

### Staleness Check

Before recalculating, the worker checks if the existing `MARKET_AVERAGES` document has a timestamp older than the new listing. If not, the recalculation is skipped (the data hasn't changed).

### Aggregation Pipeline

`calculate_listing_averages()` runs a MongoDB aggregation pipeline:

```
1. $match      - Filter by name, shiny, tier
2. $addFields  - Create unitIndex array [0..amount-1]
3. $unwind     - Expand each unit as a separate data point
4. $sort       - Sort by listing_price ascending
5. $group      - Compute statistics:
                  - identifiedPrices array (sorted)
                  - unidentifiedPrices array (sorted)
                  - min, max, avg for both categories
                  - count for both categories
6. $project    - Compute final fields:
                  - p50_price (median from sorted array)
                  - average_mid_80_percent_price (trimmed mean)
```

#### Amount Expansion

A listing with `amount=4` and `listing_price=1000` is expanded into 4 data points, each worth 1000. This weights price statistics by volume.

#### Median (P50)

Computed directly from the sorted price array using MongoDB's `$arrayElemAt`:
- **Odd count:** middle element
- **Even count:** average of two middle elements

#### Mid-80% Trimmed Mean

Discards the bottom 10% and top 10% of prices (by count after amount expansion), then computes the mean of the remaining 80%. Falls back to the full average if fewer than 3 data points.

### Tiered Items

Items of type `MaterialItem`, `PowderItem`, `AmplifierItem`, and `EmeraldPouchItem` use the `tier` field for grouping. Statistics are computed per-tier. Non-tiered items always have `tier=null`.

### 7-Day Exponential Moving Average (EMA)

The EMA smooths the P50 price over a 7-day window using:

```
EMA = alpha * current_p50 + (1 - alpha) * previous_ema
alpha = 2 / (7 + 1) = 0.25
```

**Calendar-day anchoring:** The EMA prior is always read from `MARKET_ARCHIVE` (yesterday's immutable snapshot), not from `MARKET_AVERAGES`. This ensures:
- All recalculations within the same day use the same prior
- The EMA only advances when the nightly archive job runs
- The value is stable intraday regardless of how many listings arrive

**Fallback chain for prior:**
1. `average_p50_ema_price` from archive
2. `p50_price` from archive
3. `average_mid_80_percent_price` from archive (legacy docs)
4. Bootstrap from current P50 (no archive history)

The same logic applies independently for unidentified listings.

## Listing Queries

### Filter Logic

`get_trade_market_item_listings()` builds a MongoDB query filter:

- **Name:** case-insensitive regex match (`.*{name}.*`)
- **Shiny:** `shiny_stat != null` (true) or `shiny_stat == null` (false)
- **Unidentified:** exact boolean match
- **Rarity:** case-insensitive regex; "Normal" also matches `null` rarity
- **Tier:** only applied for tiered item types; for non-tiered types, tier filter is ignored
- **Item type / Sub type:** exact match

When both `item_name` and `tier` are provided without an explicit `item_type`, an `$or` filter ensures non-tiered items are included alongside tiered items matching the specified tier.

### Sorting

Six sort options are available via the `SortOption` enum:

| Sort Value | MongoDB Field | Direction |
|-----------|---------------|-----------|
| `timestamp_desc` | `timestamp` | -1 |
| `timestamp_asc` | `timestamp` | 1 |
| `listing_price_desc` | `listing_price` | -1 |
| `listing_price_asc` | `listing_price` | 1 |
| `overall_roll_desc` | `overall_roll` | -1 |
| `overall_roll_asc` | `overall_roll` | 1 |

### Pagination

Standard skip/limit pagination:
- `page` minimum: 1
- `page_size` maximum: 1000
- Response includes `page`, `page_size`, `count` (returned items), `total` (matching items)

### Privacy

The `player_name` field is excluded from query results via a MongoDB projection.

## Price History

`get_price_history()` queries `MARKET_ARCHIVE` for daily snapshots within a date range:

- Default range: 7 days ending yesterday
- Date filter uses half-open interval: `[start_date, end_date + 1 day)`
- Results sorted by timestamp ascending
- Tier filtering uses the same tiered/non-tiered `$or` logic

## Historic Averages

`get_historic_average()` aggregates across multiple archive documents:

```
$match -> $group (avg of each stat field, sum of counts) -> $project
```

Returns a single document with averaged statistics over the date range, plus a `document_count` field indicating how many daily snapshots were included.

## Ranking

`get_all_items_ranking()` aggregates across `MARKET_ARCHIVE`:

1. Match date range (non-shiny items only)
2. Group by `(name, tier)` -- compute min, max, avg prices and total counts
3. Sort by `average_price` descending
4. Enumerate with a `rank` field starting at 1

The ranking reflects settled market data from archived snapshots, not intraday fluctuations.
