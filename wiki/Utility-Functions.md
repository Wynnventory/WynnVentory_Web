# Utility Functions

## Parameter Parsing

**Source:** `modules/utils/param_utils.py`

### parse_date_params(start_str, end_str)

Parses ISO date strings (`YYYY-MM-DD`) into `datetime` objects. Returns a tuple of `(start_date, end_date, error)`. If parsing fails, `error` contains `{"error": "Invalid date format. Use YYYY-MM-DD."}`.

### parse_boolean_param(param_value, default=False)

Converts string `"true"`/`"false"` to Python `bool`. Returns `default` if `param_value` is `None`.

### parse_tier_param(tier_param)

Converts a string tier value to `int`. Returns `None` if input is `None`.

### api_response(data, status_code=200)

Wraps data in a `jsonify()` Flask response with the given status code.

### handle_request_error(exception, error_msg, status_code=500)

Logs the exception with stack trace and returns a standardized error response:

```json
{"error": "error_msg"}
```

## Icon Mapping

**Source:** `modules/utils/utils.py`

### map_local_icons(icon_name)

Maps Wynncraft icon identifiers to local static asset paths:

| Icon Name | Local Path |
|-----------|-----------|
| `helmet` | `helmet_diamond.webp` |
| `chestplate` | `chestplate_diamond.webp` |
| `leggings` | `leggings_diamond.webp` |
| `boots` | `boots_diamond.webp` |

Used when serializing `Item` objects via `to_dict()`.

## Template Filters

**Source:** `modules/__init__.py`

These Jinja2 template filters are registered with the Flask app for use in HTML templates. They are not used by the API endpoints.

### emerald_format(emeralds)

Converts a raw emerald count into Wynncraft's currency notation:

| Unit | Value |
|------|-------|
| `stx` (stacks) | 64^3 = 262,144 emeralds |
| `le` (liquid emeralds) | 64^2 = 4,096 emeralds |
| `eb` (emerald blocks) | 64 emeralds |
| `e` (emeralds) | 1 emerald |

Examples:
- `262144` -> `"1stx"`
- `266240` -> `"1stx 1le"`
- `4160` -> `"1le 1eb"`
- `65` -> `"1eb 1e"`
- `0` -> `"0e"`

When the value is in stacks, the LE portion is shown as a decimal with trailing zeros stripped.

### last_updated(value)

Converts a timestamp to a human-readable "X minutes/hours/days" ago string:

1. Parses ISO-8601 string or datetime (must be timezone-aware)
2. Computes difference from now
3. Returns: `"X minute(s)"`, `"X hour(s)"`, or `"X day(s)"`

Returns `"Invalid timestamp"` for naive datetimes or unparseable values.

### to_roman(num)

Converts an integer to a Roman numeral string. Returns the input unchanged for non-integer values.

## Pydantic Schemas

**Source:** `modules/schemas/item_search.py`

### ItemSearchRequest

Validates the request body for `POST /api/items`:

| Field | Type | Default | Validation |
|-------|------|---------|-----------|
| `query` | str | None | Free-text search |
| `type` | list[str] | `[]` | Item type filter |
| `tier` | list[int] | `[]` | Tier filter |
| `attackSpeed` | list[int] | `[]` | Attack speed filter |
| `levelRange` | tuple[int, int] | `[0, 110]` | Min/max level |
| `professions` | list[str] | `[]` | Profession filter |
| `identifications` | list[str] | `[]` | Stat identification filter |
| `majorIds` | list[str] | `[]` | Major ID filter |
| `page` | int | 1 | Must be >= 1 |
