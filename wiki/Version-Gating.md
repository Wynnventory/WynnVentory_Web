# Version Gating

**Source:** `modules/utils/version.py`

## Overview

The version gating system ensures that only submissions from sufficiently recent versions of the WynnVentory mod are accepted. This allows the backend to deprecate old data formats without breaking compatibility immediately.

## How It Works

Every submission (market listing, pool data, gambit) includes a `modVersion` field. The service layer calls:

```python
compare_versions(mod_version, Config.MIN_SUPPORTED_VERSION)
```

If the mod version is below the minimum, the submission is silently dropped (market listings) or raises a `ValueError` (pool data).

## Version Comparison

### compare_versions(to_test, min_version) -> bool

Returns `True` if `to_test >= min_version`.

Comparison is done segment by segment (dot-separated), with zero-padding for unequal segment counts.

### VersionPart

Each dot-separated segment is parsed into a `VersionPart` with a numeric prefix and string suffix:

| Input | Numeric | Suffix |
|-------|---------|--------|
| `"3"` | 3 | `""` |
| `"3a"` | 3 | `"a"` |
| `"3-dev"` | 3 | `"-dev"` |
| `"beta2"` | 0 | `"beta2"` |

### Comparison Precedence

1. **Numeric prefix** -- higher number wins
2. **Suffix** (same numeric):
   - `dev` / `beta` suffixes rank **highest** (development versions are treated as newer)
   - Empty suffix (final release) ranks next
   - Any other suffix (pre-release) ranks lowest
   - Between two non-dev, non-empty suffixes: lexicographic comparison

### Examples

```
"1.2.0"     >= "1.2.0"     -> True   (equal)
"1.2.1"     >= "1.2.0"     -> True   (patch higher)
"1.3.0"     >= "1.2.0"     -> True   (minor higher)
"2.0.0"     >= "1.2.0"     -> True   (major higher)
"1.1.0"     >= "1.2.0"     -> False  (minor lower)
"1.2.0-dev" >= "1.2.0"     -> True   (dev > final)
"1.2.0a"    >= "1.2.0"     -> False  (pre-release < final)
"1.2"       >= "1.2.0"     -> True   (zero-padded, equal)
```

## Configuration

The minimum supported version is set via the `MIN_SUPPORTED_VERSION` environment variable and loaded by `Config`:

```python
MIN_SUPPORTED_VERSION = env_config("MIN_SUPPORTED_VERSION", default=None)
```

When `None`, no version gating is applied (all versions are accepted).

## Where Version Gating Is Applied

| Domain | Location | Behavior on Failure |
|--------|----------|-------------------|
| Market listings | `market_service.save_items()` | Item silently skipped |
| Loot pool | `base_pool_service.save()` | `ValueError` raised |
| Raid pool | `base_pool_service.save()` | `ValueError` raised |
| Gambits | `raidpool_service.save_gambits()` | Individual gambit skipped |
