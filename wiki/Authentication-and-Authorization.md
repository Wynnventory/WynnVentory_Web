# Authentication and Authorization

**Source:** `modules/auth.py`

## Overview

The API uses a token-based authentication system with two key types and scope-based authorization. All non-public endpoints require a valid API key.

## Key Types

### Public Endpoints

Endpoints decorated with `@public_endpoint` skip authentication entirely. Anyone can call them without a key.

Currently public endpoints:
- `GET /api/trademarket/history/{item_name}` -- price history
- `GET /api/trademarket/ranking` -- item ranking
- `GET /api/item/{item_name}` -- single item lookup
- `POST /api/items` -- item search

### Mod Key

A single shared API key embedded in the WynnVentory game mod. The server stores its SHA-256 hash in the `MOD_API_KEY` environment variable.

The mod key operates under a **default-deny** policy:
- It can only access endpoints explicitly marked with `@mod_allowed`
- It does not carry individual scopes
- If a mod key attempts to access a non-whitelisted endpoint, the server returns `403`

Mod-allowed endpoints:
- `POST /api/trademarket/items` (submit listings)
- `GET /api/trademarket/item/{item_name}/price` (price lookup)
- `GET /api/trademarket/history/{item_name}/price` (archive price)
- `POST /api/lootpool/items` (submit loot pool)
- `GET /api/lootpool/current` (raw current loot pool)
- `POST /api/raidpool/items` (submit raid pool)
- `GET /api/raidpool/current` (raw current raid pool)
- `POST /api/raidpool/gambits` (submit gambits)

### Scoped API Keys

Developer keys stored in the `api_keys` collection (admin database) with fields:
- `key_hash` -- SHA-256 hash of the raw key
- `owner` -- human-readable owner identifier
- `scopes` -- list of permission strings
- `revoked` -- boolean flag

## Scopes

| Scope | Grants Access To |
|-------|-----------------|
| `write:market` | Submit trade market listings |
| `read:market` | Read live listings and price statistics |
| `read:market_archive` | Read historical (archived) price data |
| `write:lootpool` | Submit loot pool data |
| `read:lootpool` | Read loot pool data |
| `write:raidpool` | Submit raid pool data |
| `read:raidpool` | Read raid pool data |

## Authentication Flow

```
1. Extract token from headers:
   - Authorization: Api-Key <token>   (preferred)
   - X-API-Key: <token>               (alternative)

2. SHA-256 hash the token

3. Query api_keys collection:
   db.api_keys.find_one({key_hash: hash, revoked: false})

4. If not found --> 403 "Invalid or revoked API key"

5. Store in Flask g context:
   g.api_key_hash = hash
   g.owner        = key_doc["owner"]
   g.scopes       = key_doc["scopes"]
   g.is_mod_key   = (hash == MOD_KEY_HASH)

6. If mod key AND endpoint not in _mod_allowed_endpoints:
   --> 403 "Forbidden, mod key not allowed on this endpoint"
```

## Scope Enforcement

The `@require_scope(scope)` decorator wraps a route function and checks:

```python
if scope not in g.scopes:
    return 403 "Forbidden, missing scope"
```

The mod key has no scopes -- it relies entirely on the `@mod_allowed` whitelist. When the mod key accesses a `@mod_allowed` endpoint, the `@require_scope` check is effectively bypassed because the mod key is already validated by the `require_api_key` middleware.

**Important:** `@require_scope` and `@mod_allowed` must both be applied to endpoints that need both scoped-key and mod-key access. The mod key's whitelist check happens in `require_api_key()` (before the route runs), while `@require_scope` runs inside the route handler.

## Usage Tracking

After every authenticated request, `record_api_usage()` enqueues a usage record:

```python
{
    "owner": g.owner,
    "key_hash": g.api_key_hash
}
```

These are buffered in memory by `UsageRepository` and flushed to the `api_usage` collection in batches of 1000 via MongoDB `$inc` upserts.

## Error Responses

| HTTP Status | Body | Cause |
|-------------|------|-------|
| `401` | `{"error": "Missing API key"}` | No key in headers |
| `403` | `{"error": "Invalid or revoked API key"}` | Key not found or revoked |
| `403` | `{"error": "Forbidden, missing scope"}` | Key lacks required scope |
| `403` | `{"error": "Forbidden, mod key not allowed on this endpoint"}` | Mod key on non-whitelisted endpoint |
