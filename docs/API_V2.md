# WynnVentory API v2 Reference

The standardized WynnVentory API. Related documents:

- **[api-v2-conventions.md](api-v2-conventions.md)** — the contract every v2
  endpoint follows (envelope, error codes, naming, dates, pagination).
- **[openapi_v2.yaml](openapi_v2.yaml)** — machine-readable OpenAPI 3.1 spec
  (importable into Swagger UI, Postman, or code generators).
- **[API_V2_MIGRATION.md](API_V2_MIGRATION.md)** — changelog and migration
  guide from the legacy v1 endpoints.
- **[API.md](API.md)** — the frozen legacy v1 reference.

Base URL: `https://wynnventory.com/api/v2` · Auth:
`Authorization: Api-Key <key>` or `X-API-Key: <key>` on every request.
Self-service keys: <https://wynnventory.com/developer/api-key>.

## Endpoints

| Method | Path | Scope | Returns |
|---|---|---|---|
| GET | `/status` | — | Key-validity probe: `{"data": {"status": "ok", "version": "v2"}}` |
| GET | `/market/listings` | `read:market` | Paginated live listings. Filters: `item_name` (substring), `item_type`, `subtype`, `rarity`, `tier`, `shiny`, `unidentified`, `sort` |
| GET | `/market/items/{name}/price` | `read:market` | Current price statistics; `shiny`, `tier` params; 404 when unknown |
| GET | `/market/items/{name}/history` | `read:market` | Paginated daily archive snapshots; `start_date`, `end_date`, `shiny`, `tier` |
| GET | `/market/items/{name}/history/latest` | `read:market_archive` | Aggregated statistics over the range; 404 when empty. Pure aggregate with its own smaller field set (`AggregatedPriceStats` in the spec): adds `document_count`, omits the per-snapshot fields (`shiny`, `timestamp`, `item_type`, `icon`, unidentified lowest/highest) |
| GET | `/market/rankings` | `read:market` | Paginated price ranking; `start_date`, `end_date` |
| GET | `/items/{name}` | key only | Wynncraft item (cached proxy); 404 when unknown |
| POST | `/items/batch` | key only | `{"item_names": [1..100]}` → name → item-or-null map |
| GET | `/aspects/{class}/{aspect}` | key only | Wynncraft class aspect (cached proxy); 404 when unknown |
| GET | `/lootpools` | `read:lootpool` | Paginated stored pool weeks (`page_size` ≤ 8), newest first |
| GET | `/lootpools/current` | `read:lootpool` | Current week's pool; 404 when absent |
| GET | `/lootpools/current/items` | `read:lootpool` | Processed current-week items, grouped |
| GET | `/lootpools/{year}/{week}` | `read:lootpool` | Specific week; 404 when absent |
| GET | `/raidpools`, `/raidpools/current`, `/raidpools/current/items`, `/raidpools/{year}/{week}` | `read:raidpool` | Same shapes as lootpools |
| GET | `/gambits/current` | `read:raidpool` | Current gambit day; 404 when absent |

All list endpoints take `page` / `page_size` and return the standard
`pagination` object. All prices are emeralds; all timestamps are ISO-8601 UTC
(`2026-08-31T12:00:00Z`).

For the meaning of the computed price fields (`average_mid_80_percent_price`,
`average_p50_ema_price`, ...), see the
[Price Fields Reference in API.md](API.md#price-fields-reference) — the
semantics are identical on v2; only names/casing of the surrounding object
differ as described in the migration guide.

## Sort options (`/market/listings`)

`timestamp_desc` (default), `timestamp_asc`, `listing_price_desc`,
`listing_price_asc`, `overall_roll_desc`, `overall_roll_asc`.

## Vocabulary

- `item_type` (market): `gear`, `material`, `ingredient`, `powder`, `rune`,
  `dungeon_key`, `amplifier`, `emerald_pouch` (in pools also `aspect`,
  `tome`, `emerald`, `weapon`, `armour`, `accessory`)
- `subtype`: lowercase sub-category — gear: `bow`, `wand`, `spear`, `dagger`,
  `relik`, `helmet`, `chestplate`, `leggings`, `boots`, `ring`, `bracelet`,
  `necklace`; powders: `waterpowder`, `firepowder`, `thunderpowder`,
  `airpowder`, `earthpowder`; runes: `uthrune`, `azrune`, `niirune`,
  `tolrune`. Filters are matched case-insensitively, so every emitted value
  round-trips as a filter
- `rarity`: `normal`, `unique`, `rare`, `legendary`, `fabled`, `mythic`, `set`

## Keeping the spec honest

`tests/test_v2_openapi.py` fails CI when the registered routes and
`openapi_v2.yaml` drift apart. When changing a request model, run
`python scripts/generate_openapi_schemas.py` and update the YAML.
