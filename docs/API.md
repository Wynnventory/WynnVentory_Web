# WynnVentory API Documentation

WynnVentory is a data aggregation service for the Wynncraft MMORPG. It collects trade market listings, loot pools, and raid pools submitted by the WynnVentory game mod, computes price statistics, and exposes all data through a REST API.

---

## Table of Contents

1. [Base URL and Versioning](#base-url-and-versioning)
2. [Authentication](#authentication)
   - [Header Formats](#header-formats)
   - [Key Types](#key-types)
   - [Scopes](#scopes)
   - [Error Responses](#error-responses)
3. [Response Envelope](#response-envelope)
4. [Trade Market — Listings](#trade-market--listings)
   - [POST /api/trademarket/items](#post-apitrademarket-items)
   - [GET /api/trademarket/listings](#get-apitrademarketlistings)
   - [GET /api/trademarket/listings/{item_name}](#get-apitrademarketlistingsitem_name)
5. [Trade Market — Price](#trade-market--price)
   - [GET /api/trademarket/item/{item_name}/price](#get-apitrademarketitemitem_nameprice)
6. [Trade Market — History](#trade-market--history)
   - [GET /api/trademarket/history/{item_name}](#get-apitrademarkethistoryitem_name)
   - [GET /api/trademarket/history/{item_name}/price](#get-apitrademarkethistoryitem_nameprice)
7. [Trade Market — Ranking](#trade-market--ranking)
   - [GET /api/trademarket/ranking](#get-apitrademarketranking)
8. [Items (Wynncraft Database)](#items-wynncraft-database)
   - [GET /api/item/{item_name}](#get-apiitemitem_name)
   - [POST /api/items](#post-apiitems)
9. [Aspects](#aspects)
   - [GET /api/aspect/{class_name}/{aspect_name}](#get-apiaspectclass_nameaspect_name)
10. [Loot Pool](#loot-pool)
    - [POST /api/lootpool/items](#post-apilootpoolitems)
    - [GET /api/lootpool/items](#get-apilootpoolitems)
    - [GET /api/lootpool/current](#get-apilootpoolcurrent)
    - [GET /api/lootpool/all](#get-apilootpoolall)
    - [GET /api/lootpool/{year}/{week}](#get-apilootpoolyearweek)
11. [Raid Pool](#raid-pool)
    - [POST /api/raidpool/items](#post-apiraidpoolitems)
    - [GET /api/raidpool/items](#get-apiraidpoolitems)
    - [GET /api/raidpool/current](#get-apiraidpoolcurrent)
    - [GET /api/raidpool/all](#get-apiraidpoolall)
    - [GET /api/raidpool/{year}/{week}](#get-apiraidpoolyearweek)
    - [POST /api/raidpool/gambits](#post-apiraidpoolgambits)
    - [GET /api/raidpool/gambits/current](#get-apiraidpoolgambitscurrent)
12. [Price Fields Reference](#price-fields-reference)
13. [Concepts: Data Flow](#concepts-data-flow)
14. [Item Types Reference](#item-types-reference)

---

## Base URL and Versioning

All endpoints are served under the `/api` prefix. There is no explicit version segment in the path; breaking changes are communicated through the `modVersion` field in submissions and the `MIN_SUPPORTED_VERSION` server-side gate.

| Environment | Base URL                          |
|-------------|-----------------------------------|
| Production  | `https://wynnventory.com`         |
| Development | `http://localhost:5000`           |

---

## Authentication

### Header Formats

Every request that is not marked **Public** must include an API key in one of the following headers. Both formats are equivalent; use whichever is more convenient for your client.

```
Authorization: Api-Key <your-key>
```

```
X-API-Key: <your-key>
```

The server hashes the provided token with SHA-256 and looks it up in the database. Keys that have been revoked are rejected even if the hash otherwise matches.

### Key Types

| Type | Description |
|------|-------------|
| **Public** | No key required. The endpoint is open to all callers. |
| **Mod Key** | A single shared key embedded in the WynnVentory game mod. Operates under a default-deny policy — it can only call endpoints explicitly marked as mod-allowed. It carries no individual owner scopes. |
| **Scoped Key** | A regular API key issued to a developer or service. Access to each endpoint is controlled by the scopes attached to the key. |

### Scopes

| Scope | Grants Access To |
|-------|-----------------|
| `write:market` | Submit trade market listings |
| `read:market` | Read live market listings and price statistics |
| `read:market_archive` | Read historical (archived) price data |
| `write:lootpool` | Submit loot pool data |
| `read:lootpool` | Read loot pool data |
| `write:raidpool` | Submit raid pool data |
| `read:raidpool` | Read raid pool data |

A key may hold any combination of scopes. Scoped keys are created server-side via the `scripts/create_api_key.py` utility.

### Error Responses

All authentication and authorization failures return JSON with an `error` field.

| HTTP Status | Body | Cause |
|-------------|------|-------|
| `401` | `{ "error": "Missing API key" }` | No key was provided in the request headers |
| `403` | `{ "error": "Invalid or revoked API key" }` | The key does not exist in the database or has been revoked |
| `403` | `{ "error": "Forbidden, missing scope" }` | The key exists but lacks the required scope for this endpoint |
| `403` | `{ "error": "Forbidden, mod key not allowed on this endpoint" }` | The mod key was used on an endpoint that has not been explicitly opened to it |

---

## Response Envelope

Most endpoints return data directly as a JSON object or array without an outer envelope. The `api_response` helper sets the HTTP status code alongside the JSON body. Error bodies always include an `error` key.

**Success:**
```json
{ "message": "Items received successfully" }
```

**Error:**
```json
{ "error": "Internal server error" }
```

Paginated endpoints return a top-level object with pagination metadata alongside the `items` array (see individual endpoint documentation for the exact shape).

---

## Trade Market — Listings

### POST /api/trademarket/items

Submit one or more trade market listings from the game mod. Each listing represents an item currently available for sale on the in-game trade market.

**Auth:** `write:market` scope required. The Mod Key is also accepted on this endpoint.

**Request body:** `application/json` — an array of listing objects.

```json
[
  {
    "item": {
      "name": "Divzer",
      "rarity": "Legendary",
      "itemType": "Weapon",
      "type": "Bow",
      "tier": null,
      "unidentified": false,
      "shinyStat": null,
      "overallRollPercentage": 87.4,
      "actualStatsWithPercentage": {
        "dexterity": 95.2,
        "speed": 88.1
      },
      "rerollCount": 0,
      "icon": "bow_icon_url"
    },
    "amount": 1,
    "listingPrice": 15000,
    "playerName": "SomePlayer",
    "modVersion": "1.2.0",
    "hash_code": "abc123def456"
  }
]
```

**Listing object fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `item` | object | Yes | Item descriptor object (see below) |
| `amount` | integer | Yes | Number of items in the listing |
| `listingPrice` | integer | Yes | Sale price in emeralds |
| `playerName` | string | Yes | In-game name of the seller |
| `modVersion` | string | Yes | WynnVentory mod version that produced this payload. Must meet the server's `MIN_SUPPORTED_VERSION` threshold or the listing is silently dropped. |
| `hash_code` | string | Yes | Unique hash for deduplication |

**Item descriptor fields:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Item name as it appears in Wynncraft |
| `rarity` | string | e.g. `"Normal"`, `"Unique"`, `"Rare"`, `"Legendary"`, `"Fabled"`, `"Mythic"`, `"Set"` |
| `itemType` | string | Broad category: `"Weapon"`, `"Armour"`, `"Accessory"`, `"MaterialItem"`, `"PowderItem"`, `"AmplifierItem"`, `"EmeraldPouchItem"` |
| `type` | string | Sub-type within the category (e.g. `"Bow"`, `"Helmet"`, `"Ring"`) |
| `tier` | integer or null | Tier level. Used only for tiered item types (`MaterialItem`, `PowderItem`, `AmplifierItem`, `EmeraldPouchItem`). `null` for all other types. |
| `unidentified` | boolean | Whether the item is unidentified |
| `shinyStat` | string or null | Name of the shiny stat if the item is shiny, otherwise `null` |
| `overallRollPercentage` | float or null | Composite roll quality percentage (0–100). `null` for unidentified items. |
| `actualStatsWithPercentage` | object or null | Map of stat name to roll percentage. `null` for unidentified items. |
| `rerollCount` | integer | Number of times the item has been re-rolled |
| `icon` | string or null | URL or resource identifier for the item's icon |

**Success response:** `200 OK`

```json
{ "message": "Items received successfully" }
```

**Error responses:**

| Status | Body | Cause |
|--------|------|-------|
| `400` | `{ "error": "No items provided" }` | Request body was empty or an empty array |
| `400` | `{ "error": "Validation error while processing items" }` | One or more items failed validation |
| `500` | `{ "error": "Internal server error" }` | Unexpected processing failure |

**Example curl:**

```bash
curl -X POST https://wynnventory.com/api/trademarket/items \
  -H "Authorization: Api-Key YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "item": {
        "name": "Divzer",
        "rarity": "Legendary",
        "itemType": "Weapon",
        "type": "Bow",
        "tier": null,
        "unidentified": false,
        "shinyStat": null,
        "overallRollPercentage": 87.4,
        "actualStatsWithPercentage": { "dexterity": 95.2, "speed": 88.1 },
        "rerollCount": 0,
        "icon": "bow_icon_url"
      },
      "amount": 1,
      "listingPrice": 15000,
      "playerName": "SomePlayer",
      "modVersion": "1.2.0",
      "hash_code": "abc123def456"
    }
  ]'
```

---

### GET /api/trademarket/listings

### GET /api/trademarket/listings/{item_name}

Retrieve paginated live trade market listings. Both routes are identical in behavior; providing `item_name` in the path is equivalent to filtering by `item_name` as a query parameter and is offered for convenience.

**Auth:** `read:market` scope required. The Mod Key is not accepted on this endpoint.

**Path parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `item_name` | string | Optional. Partial, case-insensitive name match against the item's `name` field. |

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `rarity` | string | — | Filter by rarity. Accepted values: `Normal`, `Unique`, `Rare`, `Legendary`, `Fabled`, `Mythic`, `Set` |
| `shiny` | string | — | `"true"` or `"false"`. When `"true"`, returns only listings with a non-null `shiny_stat`. |
| `unidentified` | string | — | `"true"` or `"false"`. Filter by identification status. |
| `tier` | integer | — | Filter by tier. Only meaningful for tiered item types. |
| `itemType` | string | — | Filter by broad item type (e.g. `"Weapon"`, `"Armour"`, `"MaterialItem"`) |
| `subType` | string | — | Filter by sub-type (e.g. `"Bow"`, `"Spear"`, `"Helmet"`) |
| `sort` | string | `timestamp_desc` | Sort order. See table below. |
| `page` | integer | `1` | Page number. Minimum value: `1`. |
| `page_size` | integer | `50` | Results per page. Maximum value: `1000`. |

**Sort options:**

| Value | Description |
|-------|-------------|
| `timestamp_desc` | Newest listings first (default) |
| `timestamp_asc` | Oldest listings first |
| `listing_price_desc` | Highest price first |
| `listing_price_asc` | Lowest price first |
| `overall_roll_desc` | Highest overall roll percentage first |
| `overall_roll_asc` | Lowest overall roll percentage first |

**Success response:** `200 OK`

```json
{
  "page": 1,
  "page_size": 50,
  "count": 12,
  "total": 12,
  "items": [
    {
      "name": "Divzer",
      "rarity": "Legendary",
      "item_type": "Weapon",
      "type": "Bow",
      "tier": null,
      "unidentified": false,
      "shiny_stat": null,
      "overall_roll": 87.4,
      "stat_rolls": { "dexterity": 95.2, "speed": 88.1 },
      "reroll_count": 0,
      "amount": 1,
      "listing_price": 15000,
      "icon": "bow_icon_url",
      "mod_version": "1.2.0",
      "hash_code": "abc123def456",
      "timestamp": "2026-03-14T12:00:00Z"
    }
  ]
}
```

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `page` | integer | Current page number |
| `page_size` | integer | Number of results per page as requested |
| `count` | integer | Number of items returned in this response |
| `total` | integer | Total number of matching items across all pages |
| `items` | array | Array of listing objects |

**Example curl:**

```bash
curl "https://wynnventory.com/api/trademarket/listings/Divzer?rarity=Legendary&sort=listing_price_asc&page=1&page_size=20" \
  -H "Authorization: Api-Key YOUR_KEY"
```

```bash
# Equivalent using query parameter
curl "https://wynnventory.com/api/trademarket/listings?item_name=divzer&rarity=Legendary" \
  -H "Authorization: Api-Key YOUR_KEY"
```

---

## Trade Market — Price

### GET /api/trademarket/item/{item_name}/price

Returns pre-computed price statistics for a specific item from the `MARKET_AVERAGES` collection. These statistics are recalculated continuously as new listings arrive and are refreshed after each nightly archive run.

**Auth:** `read:market` scope required. The Mod Key is also accepted on this endpoint.

**Path parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `item_name` | string | Yes | Exact item name (case-insensitive lookup) |

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `shiny` | string | `"false"` | `"true"` or `"false"`. When `"true"`, returns statistics for shiny versions of the item. |
| `tier` | integer | — | Tier level for tiered item types. Omit for non-tiered items. |

**Success response:** `200 OK`

```json
{
  "name": "Divzer",
  "tier": null,
  "lowest_price": 8000.0,
  "highest_price": 25000.0,
  "average_price": 14200.0,
  "average_mid_80_percent_price": 13800.0,
  "p50_price": 13500.0,
  "average_p50_ema_price": 13650.0,
  "total_count": 24,
  "unidentified_lowest_price": null,
  "unidentified_highest_price": null,
  "unidentified_average_price": null,
  "unidentified_p50_price": null,
  "unidentified_average_p50_ema_price": null,
  "unidentified_average_mid_80_percent_price": null,
  "unidentified_count": 0,
  "icon": "bow_icon_url",
  "item_type": "Weapon",
  "timestamp": "2026-03-14T12:00:00Z"
}
```

For descriptions of all price fields, see the [Price Fields Reference](#price-fields-reference) section.

**Error responses:**

| Status | Body | Cause |
|--------|------|-------|
| `400` | `{ "message": "No item name provided" }` | `item_name` path parameter was empty |
| `500` | `{ "error": "Internal server error" }` | Unexpected failure |

**Example curl:**

```bash
curl "https://wynnventory.com/api/trademarket/item/Divzer/price" \
  -H "Authorization: Api-Key YOUR_KEY"
```

```bash
# Shiny variant
curl "https://wynnventory.com/api/trademarket/item/Divzer/price?shiny=true" \
  -H "Authorization: Api-Key YOUR_KEY"
```

```bash
# Tiered item (e.g. tier 3 powder)
curl "https://wynnventory.com/api/trademarket/item/Thunder%20Powder/price?tier=3" \
  -H "Authorization: Api-Key YOUR_KEY"
```

---

## Trade Market — History

### GET /api/trademarket/history/{item_name}

Returns raw daily archive snapshots for an item over a date range. Each element in the response array corresponds to one day's archived price document. This endpoint is **Public** and requires no API key.

**Auth:** Public (no key required).

**Path parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `item_name` | string | Yes | Exact item name |

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_date` | string | 7 days ago | Start of the date range in `YYYY-MM-DD` format (inclusive) |
| `end_date` | string | Yesterday | End of the date range in `YYYY-MM-DD` format (inclusive) |
| `shiny` | string | `"false"` | `"true"` or `"false"`. Filter for shiny item history. |
| `tier` | integer | — | Tier level for tiered item types |

**Success response:** `200 OK` — Array of daily price snapshot objects. Each object has the same shape as the `/price` endpoint response, with a `timestamp` field indicating which day the snapshot represents.

```json
[
  {
    "name": "Divzer",
    "tier": null,
    "lowest_price": 8500.0,
    "highest_price": 24000.0,
    "average_price": 14000.0,
    "average_mid_80_percent_price": 13700.0,
    "p50_price": 13400.0,
    "average_p50_ema_price": 13600.0,
    "total_count": 18,
    "unidentified_lowest_price": null,
    "unidentified_highest_price": null,
    "unidentified_average_price": null,
    "unidentified_p50_price": null,
    "unidentified_average_p50_ema_price": null,
    "unidentified_average_mid_80_percent_price": null,
    "unidentified_count": 0,
    "icon": "bow_icon_url",
    "item_type": "Weapon",
    "timestamp": "2026-03-13T00:00:00Z"
  }
]
```

**Error responses:**

| Status | Body | Cause |
|--------|------|-------|
| `400` | `{ "message": "No item name provided" }` | Empty `item_name` |
| `400` | `{ "error": "Invalid date format. Use YYYY-MM-DD." }` | Malformed date string |
| `500` | `{ "error": "Internal server error" }` | Unexpected failure |

**Example curl:**

```bash
curl "https://wynnventory.com/api/trademarket/history/Divzer?start_date=2026-03-07&end_date=2026-03-13"
```

---

### GET /api/trademarket/history/{item_name}/price

Returns aggregated price statistics averaged across all archive documents in the requested date range. For backwards compatibility, this endpoint is also accessible at `GET /api/trademarket/history/{item_name}/latest`.

**Auth:** `read:market_archive` scope required. The Mod Key is also accepted on this endpoint.

**Path parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `item_name` | string | Yes | Exact item name |

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_date` | string | 7 days ago | Start of the date range in `YYYY-MM-DD` format (inclusive) |
| `end_date` | string | Yesterday | End of the date range in `YYYY-MM-DD` format (inclusive) |
| `shiny` | string | `"false"` | `"true"` or `"false"` |
| `tier` | integer | — | Tier level for tiered item types |

**Success response:** `200 OK`

```json
{
  "name": "Divzer",
  "tier": null,
  "document_count": 7,
  "lowest_price": 7500.0,
  "highest_price": 26000.0,
  "average_price": 13900.0,
  "average_mid_80_percent_price": 13500.0,
  "total_count": 168,
  "unidentified_average_price": null,
  "unidentified_average_mid_80_percent_price": null,
  "unidentified_count": 0
}
```

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `document_count` | integer | Number of daily archive documents included in the aggregation |
| `lowest_price` | float | Lowest single listing price seen across the date range |
| `highest_price` | float | Highest single listing price seen across the date range |
| `average_price` | float | Mean of all listing prices across the date range |
| `average_mid_80_percent_price` | float | Mean of the middle-80% trimmed price averaged across archive days |
| `total_count` | integer | Total number of listings observed across the date range |
| `unidentified_*` | float or null | Same statistics for unidentified variants |

**Example curl:**

```bash
curl "https://wynnventory.com/api/trademarket/history/Divzer/price?start_date=2026-03-07&end_date=2026-03-13" \
  -H "Authorization: Api-Key YOUR_KEY"
```

```bash
# Backwards-compatible alias
curl "https://wynnventory.com/api/trademarket/history/Divzer/latest?start_date=2026-03-07&end_date=2026-03-13" \
  -H "Authorization: Api-Key YOUR_KEY"
```

---

## Trade Market — Ranking

### GET /api/trademarket/ranking

Returns a ranked list of all items sorted by average price over a given date range. Data is sourced from the `MARKET_ARCHIVE` collection. This endpoint is **Public** and requires no API key.

**Auth:** Public (no key required).

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_date` | string | 7 days ago | Start of the date range in `YYYY-MM-DD` format (inclusive) |
| `end_date` | string | Yesterday | End of the date range in `YYYY-MM-DD` format (inclusive) |

**Success response:** `200 OK` — Array of ranked item objects, ordered from most expensive to least expensive.

```json
[
  {
    "rank": 1,
    "name": "Grandfather",
    "tier": null,
    "lowest_price": 50000000.0,
    "highest_price": 200000000.0,
    "average_price": 120000000.0,
    "average_mid_80_percent_price": 115000000.0,
    "average_total_count": 2.0,
    "average_unidentified_count": 0.0,
    "total_count": 14,
    "unidentified_count": 0
  }
]
```

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `rank` | integer | Position in the ranking (1 = most expensive) |
| `name` | string | Item name |
| `tier` | integer or null | Tier for tiered items, `null` otherwise |
| `lowest_price` | float | Lowest observed price across the date range |
| `highest_price` | float | Highest observed price across the date range |
| `average_price` | float | Mean price across the date range |
| `average_mid_80_percent_price` | float | Middle-80% trimmed mean across the date range |
| `average_total_count` | float | Average number of listings per day |
| `average_unidentified_count` | float | Average number of unidentified listings per day |
| `total_count` | integer | Total listing count summed across the date range |
| `unidentified_count` | integer | Total unidentified listing count summed across the date range |

**Example curl:**

```bash
curl "https://wynnventory.com/api/trademarket/ranking?start_date=2026-03-07&end_date=2026-03-13"
```

```bash
# Default date range (last 7 days)
curl "https://wynnventory.com/api/trademarket/ranking"
```

---

## Items (Wynncraft Database)

These endpoints proxy to the [Wynncraft v3 Item API](https://api.wynncraft.com/v3/item) and apply in-memory caching. They do not touch the WynnVentory database. Both endpoints are **Public**.

### GET /api/item/{item_name}

Fetch a single item's complete data from the Wynncraft item database. Results are cached for 30 minutes.

**Auth:** Public (no key required).

**Path parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `item_name` | string | Yes | Exact item name. Lookup is normalized (accent-stripped, case-folded) before comparison against the Wynncraft API response. |

**Success response:** `200 OK` — Full Wynncraft item object as returned by the upstream API.

**Not-found response:** `404`

```json
{ "message": "Item not found" }
```

**Example curl:**

```bash
curl "https://wynnventory.com/api/item/Divzer"
```

---

### POST /api/items

Search the Wynncraft item database with filters. Results are proxied from `api.wynncraft.com/v3/item/search` and cached for 5 minutes.

**Auth:** Public (no key required).

**Request body:** `application/json` — `ItemSearchRequest` object. All fields are optional.

```json
{
  "query": "Divzer",
  "type": ["Bow"],
  "tier": [],
  "attackSpeed": [],
  "levelRange": [0, 110],
  "professions": [],
  "identifications": ["dexterity"],
  "majorIds": [],
  "page": 1
}
```

**Request fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `query` | string | — | Free-text name search |
| `type` | array of strings | `[]` | Item type filter. Examples: `"Bow"`, `"Helmet"`, `"Ring"`, `"Wand"`, `"Spear"`, `"Dagger"`, `"Relik"`, `"Chestplate"`, `"Leggings"`, `"Boots"`, `"Bracelet"`, `"Necklace"` |
| `tier` | array of integers | `[]` | Tier numbers to include |
| `attackSpeed` | array of integers | `[]` | Attack speed values to include |
| `levelRange` | tuple of two integers | `[0, 110]` | Minimum and maximum combat level (inclusive) |
| `professions` | array of strings | `[]` | Profession names to filter by |
| `identifications` | array of strings | `[]` | Stat identification names to filter by (e.g. `"dexterity"`, `"speed"`) |
| `majorIds` | array of strings | `[]` | Major ID names to filter by |
| `page` | integer | `1` | Page number for Wynncraft's paginated results. Must be 1 or greater. |

**Success response:** `200 OK` — Wynncraft search result object (structure determined by the upstream API).

**Error responses:**

| Status | Body | Cause |
|--------|------|-------|
| `400` | `{ "error": "Validation error while processing items" }` | Request body failed schema validation |
| `500` | `{ "error": "Internal server error" }` | Upstream API failure or unexpected error |

**Example curl:**

```bash
curl -X POST "https://wynnventory.com/api/items" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Divzer",
    "type": ["Bow"],
    "levelRange": [80, 110],
    "identifications": ["dexterity"]
  }'
```

---

## Aspects

### GET /api/aspect/{class_name}/{aspect_name}

Fetch data for a specific class aspect from the Wynncraft v3 aspects API. Results are cached for 30 minutes. This endpoint carries no authentication decorator in the current implementation and behaves as effectively public.

**Auth:** None required.

**Path parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `class_name` | string | Yes | Wynncraft class name. Valid values: `archer`, `warrior`, `mage`, `assassin`, `shaman` |
| `aspect_name` | string | Yes | Name of the aspect to retrieve |

**Success response:** `200 OK` — Aspect object as returned by the Wynncraft aspects API.

**Error responses:**

| Status | Body | Cause |
|--------|------|-------|
| `500` | `{ "error": "Internal server error" }` | Aspect not found in the upstream response or upstream API failure |

**Example curl:**

```bash
curl "https://wynnventory.com/api/aspect/archer/Arrow%20Shield"
```

---

## Loot Pool

The loot pool represents items available in Wynncraft's weekly loot pools. A new pool is active each ISO week. Submissions are made by the game mod and processed server-side.

### POST /api/lootpool/items

Submit loot pool data from the game mod for the current week.

**Auth:** `write:lootpool` scope required. The Mod Key is also accepted on this endpoint.

**Request body:** `application/json` — Raw pool payload as produced by the game mod.

**Success response:** `200 OK`

```json
{ "message": "Items received successfully" }
```

**Error responses:**

| Status | Body | Cause |
|--------|------|-------|
| `400` | `{ "message": "No items provided" }` | Empty request body |
| `400` | `{ "error": "Validation error while processing items" }` | Validation failure |
| `500` | `{ "error": "Internal server error" }` | Unexpected failure |

**Example curl:**

```bash
curl -X POST "https://wynnventory.com/api/lootpool/items" \
  -H "Authorization: Api-Key YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{ ... }'
```

---

### GET /api/lootpool/items

Retrieve processed loot pool items for the current week. Returns a structured representation of items after server-side processing.

**Auth:** `read:lootpool` scope required.

**Success response:** `200 OK` — Processed loot pool items for the current ISO week.

**Example curl:**

```bash
curl "https://wynnventory.com/api/lootpool/items" \
  -H "Authorization: Api-Key YOUR_KEY"
```

---

### GET /api/lootpool/current

Retrieve the raw current week's loot pool document as stored in the database.

**Auth:** `read:lootpool` scope required. The Mod Key is also accepted on this endpoint.

**Success response:** `200 OK` — Raw loot pool document for the current ISO week.

**Error responses:**

| Status | Body | Cause |
|--------|------|-------|
| `404` | `{ "message": "No data found" }` | No data recorded for the current week |
| `500` | `{ "error": "Internal server error" }` | Unexpected failure |

**Example curl:**

```bash
curl "https://wynnventory.com/api/lootpool/current" \
  -H "Authorization: Api-Key YOUR_KEY"
```

---

### GET /api/lootpool/all

Retrieve a paginated list of all stored loot pool records, newest first. Page size is capped at 5 to limit the volume of weekly data returned per request.

**Auth:** `read:lootpool` scope required.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | `1` | Page number. Minimum value: `1`. |
| `page_size` | integer | `5` | Results per page. Maximum value: `5` (capped server-side). |

**Success response:** `200 OK` — Paginated list of loot pool records.

**Example curl:**

```bash
curl "https://wynnventory.com/api/lootpool/all?page=1&page_size=5" \
  -H "Authorization: Api-Key YOUR_KEY"
```

---

### GET /api/lootpool/{year}/{week}

Retrieve the loot pool for a specific ISO year and week number.

**Auth:** `read:lootpool` scope required.

**Path parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `year` | integer | Yes | Four-digit year (e.g. `2026`) |
| `week` | integer | Yes | ISO week number (1–53) |

**Success response:** `200 OK` — Loot pool document for the specified week.

**Error responses:**

| Status | Body | Cause |
|--------|------|-------|
| `500` | `{ "error": "Internal server error" }` | No data found or unexpected failure |

**Example curl:**

```bash
curl "https://wynnventory.com/api/lootpool/2026/11" \
  -H "Authorization: Api-Key YOUR_KEY"
```

---

## Raid Pool

The raid pool represents items and gambits available in Wynncraft's weekly raid rotations. The structure mirrors the loot pool API with the same week-based organization, plus additional gambit endpoints.

### POST /api/raidpool/items

Submit raid pool data from the game mod for the current week.

**Auth:** `write:raidpool` scope required. The Mod Key is also accepted on this endpoint.

**Request body:** `application/json` — Raw pool payload as produced by the game mod.

**Success response:** `200 OK`

```json
{ "message": "Items received successfully" }
```

**Example curl:**

```bash
curl -X POST "https://wynnventory.com/api/raidpool/items" \
  -H "Authorization: Api-Key YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{ ... }'
```

---

### GET /api/raidpool/items

Retrieve processed raid pool items for the current week.

**Auth:** `read:raidpool` scope required.

**Success response:** `200 OK` — Processed raid pool items for the current ISO week.

**Example curl:**

```bash
curl "https://wynnventory.com/api/raidpool/items" \
  -H "Authorization: Api-Key YOUR_KEY"
```

---

### GET /api/raidpool/current

Retrieve the raw current week's raid pool document.

**Auth:** `read:raidpool` scope required. The Mod Key is also accepted on this endpoint.

**Success response:** `200 OK` — Raw raid pool document for the current ISO week.

**Example curl:**

```bash
curl "https://wynnventory.com/api/raidpool/current" \
  -H "Authorization: Api-Key YOUR_KEY"
```

---

### GET /api/raidpool/all

Retrieve a paginated list of all stored raid pool records. Page size is capped at 5.

**Auth:** `read:raidpool` scope required.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | `1` | Page number. Minimum value: `1`. |
| `page_size` | integer | `5` | Results per page. Maximum value: `5`. |

**Example curl:**

```bash
curl "https://wynnventory.com/api/raidpool/all?page=1&page_size=5" \
  -H "Authorization: Api-Key YOUR_KEY"
```

---

### GET /api/raidpool/{year}/{week}

Retrieve the raid pool for a specific ISO year and week number.

**Auth:** `read:raidpool` scope required.

**Path parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `year` | integer | Yes | Four-digit year (e.g. `2026`) |
| `week` | integer | Yes | ISO week number (1–53) |

**Example curl:**

```bash
curl "https://wynnventory.com/api/raidpool/2026/11" \
  -H "Authorization: Api-Key YOUR_KEY"
```

---

### POST /api/raidpool/gambits

Submit gambit data from the game mod for the current week. Gambits are special raid modifiers that change raid mechanics and rewards.

**Auth:** `write:raidpool` scope required. The Mod Key is also accepted on this endpoint.

**Request body:** `application/json` — Array of gambit objects.

**Success response:** `200 OK`

```json
{ "message": "Gambits received successfully" }
```

**Error responses:**

| Status | Body | Cause |
|--------|------|-------|
| `400` | `{ "message": "No gambits provided" }` | Empty request body |
| `400` | `{ "error": "Validation error while processing gambits" }` | Validation failure |
| `500` | `{ "error": "Internal server error" }` | Unexpected failure |

**Example curl:**

```bash
curl -X POST "https://wynnventory.com/api/raidpool/gambits" \
  -H "Authorization: Api-Key YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '[{ ... }]'
```

---

### GET /api/raidpool/gambits/current

Retrieve the current week's active gambits.

**Auth:** `read:raidpool` scope required.

**Success response:** `200 OK` — Current week's gambit data as stored in the `gambit` collection.

**Example curl:**

```bash
curl "https://wynnventory.com/api/raidpool/gambits/current" \
  -H "Authorization: Api-Key YOUR_KEY"
```

---

## Price Fields Reference

The `/price` and `/history` endpoints return a set of computed price statistics. This section explains each field in detail to help you choose the right signal for your use case.

### Identified Item Statistics

| Field | Description |
|-------|-------------|
| `lowest_price` | The single lowest listing price among all live listings for the item at the time of the last averages computation. Highly sensitive to outliers. |
| `highest_price` | The single highest listing price among all live listings. Useful for estimating the top end of the market. |
| `average_price` | The simple arithmetic mean of all listing prices, weighted by listing `amount`. Susceptible to price manipulation if a few extreme outliers exist. |
| `average_mid_80_percent_price` | The arithmetic mean of prices after discarding the bottom 10% and top 10% of the price distribution (by listing amount). This trimmed mean is more resistant to outliers than `average_price` and is a reasonable fair-market estimate for most items. |
| `p50_price` | The exact median (50th percentile) of current live listings, weighted by `amount`. Half of all listed quantity is priced below this value. A robust central price signal unaffected by extreme values on either end. |
| `average_p50_ema_price` | A 7-day calendar exponential moving average (EMA) of the daily P50 price, computed with a smoothing factor of α=0.25. This value is **stable within a day** because it is only updated once per day after the nightly archive job runs. It falls back to `average_mid_80_percent_price` for items that have no P50 history yet (e.g. newly listed items). **This is the recommended price signal** when you want a historically smoothed, manipulation-resistant estimate. |
| `total_count` | The total number of identified item listings included in the statistics (summed by `amount`). A low count means the statistics are based on sparse data and should be interpreted cautiously. |

### Unidentified Item Statistics

Fields prefixed with `unidentified_` contain the same statistics calculated separately for unidentified versions of the same item. These will be `null` when no unidentified listings exist.

| Field | Description |
|-------|-------------|
| `unidentified_lowest_price` | Lowest price among unidentified listings |
| `unidentified_highest_price` | Highest price among unidentified listings |
| `unidentified_average_price` | Mean price of unidentified listings |
| `unidentified_average_mid_80_percent_price` | Middle-80% trimmed mean for unidentified listings |
| `unidentified_p50_price` | Median price of unidentified listings |
| `unidentified_average_p50_ema_price` | 7-day EMA of the daily P50 for unidentified listings |
| `unidentified_count` | Total unidentified listing count |

### Choosing the Right Price Signal

| Use Case | Recommended Field |
|----------|------------------|
| Quick fair-market estimate | `average_mid_80_percent_price` |
| Stable long-term price trend | `average_p50_ema_price` |
| Current market center point | `p50_price` |
| Checking absolute floor / ceiling | `lowest_price` / `highest_price` |
| Historical research over a date range | `/history/{item_name}/price` → `average_mid_80_percent_price` |

---

## Concepts: Data Flow

Understanding how data moves through the system helps you interpret the freshness and reliability of each endpoint's data.

### 1. Live Listings — `MARKET_LISTINGS` Collection

When the WynnVentory mod observes a trade market page in-game, it submits all visible listings via `POST /api/trademarket/items`. Each submission is validated (including a mod version gate) and written to the `MARKET_LISTINGS` MongoDB collection. This is the raw, real-time data layer.

The `GET /api/trademarket/listings` endpoints query `MARKET_LISTINGS` directly, so they reflect the most current data available.

### 2. Moving Averages — `MARKET_AVERAGES` Collection

After new listings are saved, the system asynchronously recalculates price statistics for affected items and updates the `MARKET_AVERAGES` collection. This includes all the computed fields described in the [Price Fields Reference](#price-fields-reference) section.

The `GET /api/trademarket/item/{item_name}/price` endpoint reads from `MARKET_AVERAGES`. The statistics here are current but represent a rolling window over active listings, not a point-in-time snapshot.

### 3. Nightly Archive Job — `MARKET_ARCHIVE` Collection

Each night, an archive job runs `jobs/archive_tm_items.py`, which:

1. **Copies** all documents from `MARKET_AVERAGES` into `MARKET_ARCHIVE` with the date timestamp set to the previous day. This creates an immutable daily snapshot of the market state.
2. **Deletes** listings from `MARKET_LISTINGS` that fall within the archived date window, keeping the live collection lean.
3. **Recalculates** `MARKET_AVERAGES` using the remaining (more recent) listings, and advances the `average_p50_ema_price` EMA by one day.

The `GET /api/trademarket/history` endpoints read from `MARKET_ARCHIVE`. Data here is available only for days that have already been processed by the archive job. The most recent available archive date is typically yesterday.

### 4. Rankings

The `GET /api/trademarket/ranking` endpoint aggregates across `MARKET_ARCHIVE` over a requested date range to produce a cross-item price ranking. Because it queries the archive, it reflects settled market data rather than intraday fluctuations.

### Data Flow Summary

```
Game Mod
   |
   | POST /api/trademarket/items
   v
MARKET_LISTINGS  <---> MARKET_AVERAGES  (live moving averages, intraday updates)
                             |
                   Nightly Archive Job
                             |
                             v
                    MARKET_ARCHIVE  (immutable daily snapshots)
                             |
                   GET /api/trademarket/history/*
                   GET /api/trademarket/ranking
```

### Pool Data Flow

Loot pool and raid pool data follow a simpler flow. The mod submits a raw payload for the current ISO week via the `POST` endpoints. The data is stored as-is and then retrieved via the `GET` endpoints either in its raw form (`/current`, `/{year}/{week}`) or after server-side processing into a structured format (`/items`). Pools rotate on a weekly basis; the server determines the current week using ISO week numbering, with loot pools and raid pools potentially using different week-offset logic.

---

## Item Types Reference

### Item Categories (`itemType`)

| Value | Description |
|-------|-------------|
| `Weapon` | Weapons with a sub-type (see below) |
| `Armour` | Armour pieces with a sub-type (see below) |
| `Accessory` | Accessories with a sub-type (see below) |
| `MaterialItem` | Crafting materials. Uses `tier` field. |
| `PowderItem` | Elemental powders. Uses `tier` field (tier 1–6). |
| `AmplifierItem` | Powder amplifiers. Uses `tier` field. |
| `EmeraldPouchItem` | Emerald storage pouches. Uses `tier` field. |

### Weapon Sub-types (`type`)

| Value |
|-------|
| `Bow` |
| `Wand` |
| `Spear` |
| `Dagger` |
| `Relik` |

### Armour Sub-types (`type`)

| Value |
|-------|
| `Helmet` |
| `Chestplate` |
| `Leggings` |
| `Boots` |

### Accessory Sub-types (`type`)

| Value |
|-------|
| `Ring` |
| `Bracelet` |
| `Necklace` |

### Rarity Values

| Value |
|-------|
| `Normal` |
| `Unique` |
| `Rare` |
| `Legendary` |
| `Fabled` |
| `Mythic` |
| `Set` |
