# Wynncraft API Client

**Source:** `modules/routes/api/wynncraft_api.py`

## Overview

The Wynncraft API client is a thin wrapper around the Wynncraft v3 REST API (`https://api.wynncraft.com/v3`). It provides caching and error handling for all outbound API calls.

## Base URL

```
https://api.wynncraft.com/v3
```

## Caching

### Cache Implementation

A simple in-memory TTL cache (`Cache` class):

```python
class Cache:
    cache: dict[str, {"data": Any, "expiry": float}]
```

- Cache keys are constructed from the function name and its arguments
- Expired entries are removed on access (lazy eviction)
- Only non-`None` results are cached (failed requests are not cached)
- Cache is per-process (each Gunicorn worker has its own cache)

### Cache TTLs

| Function | TTL | Description |
|----------|-----|-------------|
| `get_item_database()` | 1 hour | Full item database (large, rarely changes) |
| `search_items()` | 5 minutes | Item search results |
| `quick_search_item()` | 30 minutes | Single item lookup |
| `get_aspect_by_name()` | 30 minutes | Aspect data |

### @cached Decorator

```python
@cached(ttl=300)
def my_function(*args, **kwargs):
    ...
```

Wraps a function to check the cache before executing. If a cached result exists and hasn't expired, it's returned directly without calling the underlying function.

## Error Handling

### @api_request Decorator

Wraps API functions to catch and log:
- `HTTPError` -- HTTP status errors from the Wynncraft API
- `Timeout` -- request timeout (all requests use a 10-second timeout)
- General exceptions

On any error, the decorator returns `None` rather than raising, allowing the caller to handle the absence of data gracefully.

## API Functions

### get_item_database()

```
GET /item/database?fullResult
```

Fetches the complete Wynncraft item database. Returns a dict where keys are item names. Cached for 1 hour.

### search_items(payload, page)

```
POST /item/search?page={page}
```

Searches items using a filter payload (query, type, tier, level range, etc.). Used by the `POST /api/items` endpoint.

### quick_search_item(item_name)

```
GET /item/search/{item_name}
```

Fetches a single item by name. Performs Unicode normalization on the item name for matching:

1. Normalize to NFKD form (decompose accented characters)
2. Strip combining marks and non-ASCII characters
3. Case-fold for comparison

This handles items with accented names (e.g., Wynncraft items using diacritics).

If the response contains multiple items, only the one matching the normalized target name is returned.

### get_aspect_by_name(class_name, aspect_name)

```
GET /aspects/{class_name}
```

Fetches all aspects for a class, then extracts the specific aspect by name. Returns `None` if the aspect name isn't found.

Valid class names: `archer`, `warrior`, `mage`, `assassin`, `shaman`

## Unicode Normalization

The `clean_name()` helper ensures accurate name matching across different Unicode representations:

```python
def clean_name(name: str) -> str:
    name = unicodedata.normalize('NFKD', name)    # Decompose
    cleaned = ''.join(
        c for c in name
        if not unicodedata.combining(c) and ord(c) < 128
    )
    return cleaned.strip().casefold()
```

Example: `"Divzér"` -> `"divzer"`
