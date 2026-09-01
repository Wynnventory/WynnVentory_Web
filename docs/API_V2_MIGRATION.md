# WynnVentory API v2 — Migration Changelog

This is the changelog for API-key holders migrating an application from the
legacy `/api` endpoints to the standardized `/api/v2` surface.

**TL;DR:** every v2 response is wrapped in `{"data": ...}`, every error is
`{"error": {"code", "message"}}`, every name is snake_case, every timestamp is
ISO-8601 UTC, missing resources are real 404s, and every endpoint requires an
API key. The legacy `/api` endpoints keep working unchanged — migrate at your
own pace, but new integrations should start on v2.

---

## Endpoint mapping

| v1 (legacy) | v2 | Notes |
|---|---|---|
| `GET /api/trademarket/listings[/{name}]` | `GET /api/v2/market/listings?item_name={name}` | Path-segment filter becomes a real query param. `?sort=` now works (it always returned 500 on v1). |
| `GET /api/trademarket/item/{name}/price` | `GET /api/v2/market/items/{name}/price` | Unknown item is now `404` (was empty `{}` with 200). |
| `GET /api/trademarket/history/{name}` | `GET /api/v2/market/items/{name}/history` | Now paginated and enveloped (was a bare array); now requires a key + `read:market` (was public). |
| `GET /api/trademarket/history/{name}/price` and `/latest` | `GET /api/v2/market/items/{name}/history/latest` | The two aliases collapse into one path. Empty result is now `404`. |
| `GET /api/trademarket/ranking` | `GET /api/v2/market/rankings` | Now paginated and enveloped (was one bare array of every item); `itemType` → `item_type`; now requires a key + `read:market` (was public). |
| `GET /api/item/{name}` | `GET /api/v2/items/{name}` | Now requires a key (was public). Unsupported item types are `404` (v1 crashed with 500). |
| `POST /api/items` (Wynncraft search) | — not carried over | Use the Wynncraft v3 search API directly, or `POST /api/v2/items/batch` to resolve known names in bulk. |
| — new | `POST /api/v2/items/batch` | `{"item_names": [...]}` (1–100) → map of name → item or `null`. |
| `GET /api/aspect/{class}/{aspect}` | `GET /api/v2/aspects/{class}/{aspect}` | Now requires a key (v1 was keyless). Unknown aspect is `404` (was 500). |
| `GET /api/lootpool/all` | `GET /api/v2/lootpools` | Pagination envelope now includes `total_items`/`total_pages`. |
| `GET /api/lootpool/current` | `GET /api/v2/lootpools/current` | Missing week is `404` (was empty 200). |
| `GET /api/lootpool/items` | `GET /api/v2/lootpools/current/items` | |
| `GET /api/lootpool/{year}/{week}` | `GET /api/v2/lootpools/{year}/{week}` | Missing week is `404` (v1 could 500); out-of-range year/week is a validation `400`. |
| `GET /api/raidpool/...` | `GET /api/v2/raidpools/...` | Same four routes as lootpools. |
| `GET /api/raidpool/gambits/current` | `GET /api/v2/gambits/current` | Missing data is `404` (was empty 200). |
| `POST /api/trademarket/items`, `POST /api/{loot,raid}pool/items`, `POST /api/raidpool/gambits` | — stay on v1 | Data submission remains v1-only (used by the game mod). |
| — new | `GET /api/v2/status` | Key-validity / uptime probe. |

## Breaking changes to handle in your client

### 1. Success envelope

Every v2 success response wraps its payload:

```jsonc
// v1
[ {...}, {...} ]
// v2
{ "data": [ {...}, {...} ], "pagination": { "page": 1, "page_size": 50, "total_items": 123, "total_pages": 3 } }
```

Read `resp.data` everywhere. `pagination` appears only on collection
endpoints and always has the same four fields (v1 had three different
pagination shapes and bare arrays).

### 2. Error shape and status codes

All errors are `{"error": {"code", "message", "details?"}}` — v1's mix of
`{"error": "..."}` and `{"message": "..."}` strings is gone. Match on
`error.code`, not the message text: `validation_error`, `missing_api_key`,
`invalid_api_key`, `missing_scope`, `forbidden`, `not_found`,
`method_not_allowed`, `upstream_unavailable`, `internal_error`.

- An **invalid/revoked key is now 401** (v1: 403). Missing key stays 401.
- **"No data" is now 404** with `not_found` — v1 returned `{}`/`[]` with 200.
  Only a *filtered collection* with zero matches returns 200 + empty `data`.
- Validation problems (bad dates, unknown params, `page_size=0`, bad
  booleans) are structured 400s with a `details` array — v1 variously
  returned 400s with different bodies or crashed with 500.
- Unknown `/api/v2/...` URLs return JSON 404 — v1 redirects (302) to the
  website homepage.
- When the upstream Wynncraft API is unreachable, item/aspect endpoints
  return **502 `upstream_unavailable`** instead of pretending the resource
  does not exist — retry later rather than caching a 404.

### 3. Authentication is required everywhere

v1's public endpoints (`history`, `ranking`, `item`, `aspect`) require a key
on v2. Self-service keys from `wynnventory.com/developer/api-key` already
carry every read scope; item/aspect endpoints need no scope at all, just a
valid key.

### 4. Timestamps are ISO-8601 UTC

```
v1:  "Fri, 14 Mar 2026 12:00:00 GMT"   (RFC 1123 — despite older docs claiming ISO)
v2:  "2026-03-14T12:00:00Z"
```

Date query params (`start_date`, `end_date`) accept `YYYY-MM-DD` (as before)
or full ISO-8601, and are interpreted as UTC.

### 5. snake_case everywhere, one name per concept

| Concept | v1 | v2 |
|---|---|---|
| Item category (query + response) | `itemType` / `item_type` / `"GearItem"` / `"MaterialItem"` | `item_type`, lowercase snake_case: `gear`, `material`, `ingredient`, `powder`, `rune`, `dungeon_key`, `amplifier`, `emerald_pouch` (pools also: `aspect`, `tome`, `emerald`, `weapon`, `armour`, `accessory`) |
| Item sub-category | `subType` (query), `type`/`subtype` (responses) | `subtype`, lowercase values (`bow`, `helmet`, `ring`, ...). Compound v1 values collapse to plain lowercase: `WaterPowder` → `waterpowder`, `UthRune` → `uthrune` |
| Shiny | `shiny_stat` object only (listings), `shiny` bool (averages), both camelCase in pools | `shiny` (boolean) **and** `shiny_stat` (object or null), always both present |
| Rarity | Mixed casing per endpoint | Always lowercase in responses; filters case-insensitive |
| Pool contents | `regions` / `region_items` / `group_items` with `items`/`loot_items` | Always `groups: [{"name", "items"}]` |

### 6. Stricter query parsing

- Unknown query parameters are rejected with a 400 (catches typos like
  `?itemType=` immediately). Don't append cache-buster params.
- Booleans accept only `true`/`false`/`1`/`0` (case-insensitive). v1 treated
  anything except the literal string `true` as false.
- `page_size` limits: 200 for market collections, 8 for pools; minimum 1.

### 7. Fields removed from listings

`hash_code` and `mod_version` (internal bookkeeping) and `player_name` are
not exposed on v2 listings. If you relied on `hash_code` for deduplication,
dedupe on (`name`, `listing_price`, `amount`, `timestamp`) instead, or tell
us your use case.

## Non-breaking niceties

- CORS is enabled on all of `/api/v2` (`Access-Control-Allow-Origin: *`),
  so browser apps can call it directly.
- `GET /api/v2/status` validates your key and returns
  `{"data": {"status": "ok", "version": "v2"}}`.
- A machine-readable OpenAPI 3.1 spec lives at `docs/openapi_v2.yaml`.
- `total_items`/`total_pages` are present on every paginated response,
  including pools (v1's pool pagination had no totals).

## Worked example

```bash
# v1
curl "https://wynnventory.com/api/trademarket/listings/Divzer?rarity=Legendary&subType=Bow&page_size=20" \
  -H "Authorization: Api-Key $KEY"

# v2
curl "https://wynnventory.com/api/v2/market/listings?item_name=Divzer&rarity=legendary&subtype=bow&page_size=20" \
  -H "Authorization: Api-Key $KEY"
```

```jsonc
// v2 response (excerpt)
{
  "data": [
    {
      "name": "Divzer",
      "rarity": "legendary",
      "item_type": "weapon",
      "subtype": "bow",
      "tier": null,
      "unidentified": false,
      "shiny": false,
      "shiny_stat": null,
      "overall_roll": 87.4,
      "stat_rolls": { "dexterity": 95.2 },
      "reroll_count": 0,
      "amount": 1,
      "listing_price": 15000,
      "icon": "bow_icon_url",
      "timestamp": "2026-03-14T12:00:00Z"
    }
  ],
  "pagination": { "page": 1, "page_size": 20, "total_items": 1, "total_pages": 1 }
}
```

## Deprecation policy

The v1 endpoints remain available for the WynnVentory game mod and the
website and have **no sunset date**. v1 no longer receives behavior changes
beyond bug fixes; new features land on v2 only.
