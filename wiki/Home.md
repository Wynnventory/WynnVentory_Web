# WynnVentory Backend Wiki

WynnVentory is a data aggregation service for the Wynncraft MMORPG. The backend collects trade market listings, loot pools, and raid pools submitted by the WynnVentory game mod, computes price statistics, and exposes the data through a REST API.

## Wiki Pages

### Architecture
- [Architecture Overview](Architecture-Overview.md) - High-level system design, layered architecture, and project structure
- [Application Lifecycle](Application-Lifecycle.md) - Startup, request handling, and shutdown sequences

### Core Systems
- [Authentication and Authorization](Authentication-and-Authorization.md) - API key system, scopes, and the mod key
- [Database Layer](Database-Layer.md) - MongoDB connections, collections, and schemas
- [Queue Worker](Queue-Worker.md) - Background processing, the request queue, and graceful shutdown

### Domain Logic
- [Trade Market](Trade-Market.md) - Listing ingestion, price statistics, EMA calculation, and archival
- [Loot Pool](Loot-Pool.md) - Weekly loot pool submission, validation, and aggregation
- [Raid Pool](Raid-Pool.md) - Weekly raid pool and daily gambit handling
- [Item Models](Item-Models.md) - Domain model hierarchy for items, weapons, armour, and accessories

### Infrastructure
- [Wynncraft API Client](Wynncraft-API-Client.md) - External API integration and caching
- [Time Validation](Time-Validation.md) - Reset schedules, week calculation, and timestamp validation
- [Version Gating](Version-Gating.md) - Mod version comparison and minimum version enforcement
- [Deployment](Deployment.md) - Gunicorn configuration, Heroku deployment, and the archive job

### Reference
- [Configuration](Configuration.md) - Environment variables and the Config class
- [Utility Functions](Utility-Functions.md) - Parameter parsing, error handling, and icon mapping
- [API Documentation](../docs/API.md) - Full endpoint reference (separate from this wiki)
