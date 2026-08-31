# WynnVentory API v2 — Conventions

This document is the contract for every endpoint under `/api/v2`. New v2
endpoints MUST follow it; deviations require updating this document first.
The v1 surface under `/api` is frozen for the game mod and the website and is
NOT covered by these rules.

## Base URL and versioning

All standardized endpoints live under `/api/v2`. Breaking changes to this
surface will ship as `/api/v3`; `/api/v2` responses only change additively
(new fields, new endpoints).

## Authentication

Every `/api/v2` request requires a valid API key (there are no public v2
endpoints). Both header forms are accepted:

```
Authorization: Api-Key <your-key>
X-API-Key: <your-key>
```

| Status | Code | Cause |
|---|---|---|
| 401 | `missing_api_key` | No key provided (`WWW-Authenticate: Api-Key` is set) |
| 401 | `invalid_api_key` | Key unknown or revoked (`WWW-Authenticate: Api-Key` is set) |
| 403 | `missing_scope` | Valid key without the required scope |
| 403 | `forbidden` | The shared mod key (it is pinned to the v1 surface) |

Note: v1 returns 403 for invalid keys; v2 deliberately uses 401 for both
missing and invalid credentials.

CORS preflight (`OPTIONS`) requests bypass authentication, and every v2
response carries `Access-Control-Allow-Origin: *`.

## Success envelope

Every success response is a JSON object with a `data` key. Paginated
collections additionally carry `pagination`:

```json
{ "data": { ... } }
```

```json
{
  "data": [ ... ],
  "pagination": { "page": 1, "page_size": 50, "total_items": 1234, "total_pages": 25 }
}
```

## Error envelope

Every error response is a JSON object with an `error` key:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid query parameters",
    "details": [
      { "field": "page_size", "location": "query", "message": "Input should be greater than or equal to 1" }
    ]
  }
}
```

`details` is present only for validation errors. The `code` vocabulary is
fixed: `validation_error`, `missing_api_key`, `invalid_api_key`,
`missing_scope`, `forbidden`, `not_found`, `method_not_allowed`,
`internal_error`.

## Status codes

| Status | Used for |
|---|---|
| 200 | Success. An empty filtered collection is a 200 with an empty `data` array. |
| 202 | Reserved for future asynchronous write endpoints ("accepted, not yet persisted"). |
| 400 | Malformed JSON and every request validation failure. |
| 401 | Missing or invalid API key. |
| 403 | Valid key, insufficient rights. |
| 404 | Unknown **named resource** (item, aspect, pool week) and unknown `/api/v2` path — always JSON, never a redirect. |
| 405 | Wrong HTTP method — JSON. |
| 500 | Unexpected failure. The body is always `{"error": {"code": "internal_error", "message": "Internal server error"}}`; detail goes to server logs only. |

The empty-result rule: filtering a collection (`?rarity=mythic`) can match
nothing — that is a 200. Naming a resource that does not exist
(`/market/items/NoSuchItem/price`) is a 404.

## Naming

- **snake_case** for all query parameters and all response keys.
- `item_type`: the item category, lowercase (`weapon`, `armour`, `accessory`,
  `material`, `powder`, `amplifier`, `emerald_pouch`). The storage
  vocabulary (`GearItem`, `MaterialItem`, ...) is an internal detail.
- `subtype`: the sub-category (`bow`, `helmet`, `ring`, ...). Never `type`,
  `subType`, or `sub_type`.
- `shiny` (boolean) and `shiny_stat` (object or `null`) are both always
  present on listing-shaped objects.
- `rarity` values are lowercase in responses; rarity filters match
  case-insensitively.
- Pool contents are always `groups: [{"name": ..., "items": [...]}]`,
  regardless of whether the grouping is by region or by raid.

## Dates and times

All timestamps in responses are ISO-8601 UTC with a `Z` suffix and second
precision: `"2026-08-31T12:00:00Z"`. Date-valued query parameters accept
`YYYY-MM-DD` or full ISO-8601 and are interpreted as UTC.

## Query parameters

- Booleans accept `true`, `false`, `1`, `0` (case-insensitive); anything else
  is a `validation_error`.
- Unknown query parameters are a `validation_error` (this catches client
  typos and documentation drift immediately).
- `sort` values are validated against the documented set; invalid values are
  a `validation_error` listing the allowed options.
- Pagination: `page` (default 1, min 1) and `page_size` (default 50, min 1,
  max 200; pool collections max 8).

## Writes

v2 is currently read-only. Data submission stays on the v1 surface, which the
game mod is version-pinned to. If third-party submission is ever opened up, a
v2 write endpoint will return `202` with `{"data": {"status": "accepted"}}`
semantics (writes are queued, not synchronous).
