# Architecture Overview

## System Design

WynnVentory follows a **layered architecture** with clear separation between HTTP handling, business logic, and data access.

```
Incoming Request
      |
      v
+------------------+
|   Flask Routes   |  Blueprints: market, lootpool, raidpool, item, aspect, cdn, web
+------------------+
      |
      v
+------------------+
|    Services      |  market_service, base_pool_service, raidpool_service, item_service
+------------------+
      |
      v
+------------------+
|  Repositories    |  market_repo, lootpool_repo, raidpool_repo, base_pool_repo, usage_repo
+------------------+
      |
      v
+------------------+
|    MongoDB       |  9 collections across 2 databases (current + admin)
+------------------+
```

Write operations are **asynchronous** -- the service layer enqueues validated data into a thread-safe queue, and a single background daemon thread processes items sequentially.

## Project Structure

```
WynnVentory_Web/
+-- app.py                          # Entry point, runs Flask dev server
+-- Procfile                        # Heroku deployment (gunicorn, 10 workers)
+-- requirements.txt                # Python dependencies
+-- modules/
|   +-- __init__.py                 # create_app() factory, blueprint registration
|   +-- config.py                   # Config class (env vars via python-decouple)
|   +-- db.py                       # MongoDB client management, connection pooling
|   +-- auth.py                     # API key auth middleware + scope decorators
|   +-- gunicorn_config.py          # Gunicorn worker hooks
|   +-- models/
|   |   +-- item.py                 # Base Item model
|   |   +-- weapon.py               # Weapon subclass
|   |   +-- armour.py               # Armour subclass
|   |   +-- accessory.py            # Accessory subclass
|   |   +-- base.py                 # Damage/defense base stats
|   |   +-- identification.py       # Stat identification model
|   |   +-- item_types.py           # ItemType, WeaponType, ArmorType, AccessoryType enums
|   |   +-- collection_types.py     # Collection enum (MongoDB collection names)
|   |   +-- collection_request.py   # Queue message wrapper
|   |   +-- sort_options.py         # SortOption enum for listing queries
|   +-- repositories/
|   |   +-- market_repo.py          # Trade market data access + price aggregation
|   |   +-- base_pool_repo.py       # Shared pool save/fetch logic
|   |   +-- lootpool_repo.py        # Loot pool data access + grouping pipeline
|   |   +-- raidpool_repo.py        # Raid pool data access + gambit storage
|   |   +-- usage_repo.py           # Buffered API usage tracking
|   +-- routes/
|   |   +-- api/
|   |   |   +-- market.py           # Trade market endpoints
|   |   |   +-- lootpool.py         # Loot pool endpoints (via BasePoolBlueprint)
|   |   |   +-- raidpool.py         # Raid pool + gambit endpoints
|   |   |   +-- item.py             # Item search endpoints
|   |   |   +-- aspect.py           # Aspect lookup endpoint
|   |   |   +-- base_pool_blueprint.py  # Shared pool endpoint factory
|   |   |   +-- wynncraft_api.py    # External Wynncraft API client
|   |   +-- web/                    # Web UI routes (templates, static)
|   |   +-- cdn/                    # CDN routes (public static assets)
|   +-- services/
|   |   +-- market_service.py       # Market business logic
|   |   +-- base_pool_service.py    # Pool business logic
|   |   +-- raidpool_service.py     # Gambit business logic
|   |   +-- item_service.py         # Item search/fetch logic
|   |   +-- aspect_service.py       # Aspect proxy logic
|   +-- schemas/
|   |   +-- item_search.py          # Pydantic ItemSearchRequest model
|   +-- utils/
|       +-- queue_worker.py         # Background queue + worker thread
|       +-- time_validation.py      # Wynncraft time/week calculations
|       +-- version.py              # Semantic version comparison
|       +-- param_utils.py          # Flask parameter parsing helpers
|       +-- utils.py                # Icon mapping
+-- jobs/
|   +-- archive_tm_items.py         # Nightly archive + recalculation job
+-- docs/
|   +-- API.md                      # Full API endpoint documentation
+-- tests/                          # Test suite
+-- scripts/                        # Utility scripts
```

## Key Design Decisions

### Asynchronous Write Path

All write operations (market listings, pool submissions, gambit data, API usage) are enqueued into a single in-memory `Queue` and processed by a daemon thread. This decouples HTTP response times from database write latency and allows batch processing.

### Dual Database Architecture

The system uses two MongoDB databases:
- **Current database** (dev or prod) -- stores all application data (listings, averages, archives, pools, gambits)
- **Admin database** -- stores API keys and API usage tracking

### Blueprint-Based Routing

Each API domain has its own Flask Blueprint with independent authentication middleware. The `BasePoolBlueprint` class generates standard CRUD endpoints for both loot pools and raid pools, avoiding code duplication.

### Three-Collection Market Pipeline

Market data flows through three collections:
1. `MARKET_LISTINGS` -- raw live data
2. `MARKET_AVERAGES` -- computed rolling statistics
3. `MARKET_ARCHIVE` -- immutable daily snapshots

This separation enables real-time queries, statistical analysis, and historical research independently.
