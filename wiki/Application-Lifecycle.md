# Application Lifecycle

## Startup

### Development Mode

`app.py` calls `create_app()` and runs the Flask development server:

```python
# app.py
app = create_app()
app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=(Config.ENVIRONMENT != "prod"))
```

### Production Mode (Gunicorn)

The `Procfile` launches Gunicorn with 10 worker processes:

```
web: gunicorn 'modules:create_app()' -c modules/gunicorn_config.py -w 10
```

Each Gunicorn worker calls `create_app()` independently, so each worker has its own:
- MongoDB connection pool
- Background queue worker thread
- In-memory Wynncraft API cache

### Application Factory: `create_app()`

Located in `modules/__init__.py`, this function:

1. **Creates the Flask app** with static and template folders pointing to `modules/routes/web/`
2. **Registers web/CDN blueprints** (no API key middleware)
3. **Registers API blueprints** (item, aspect, lootpool, raidpool, market) with:
   - `require_api_key` as a `before_request` hook
   - `record_api_usage` as an `after_request` hook
4. **Creates database indexes** via `ensure_debug_indexes()` (TTL index on debug logs)
5. **Registers template filters**: `emerald_format`, `last_updated`, `to_roman`
6. **Registers 404 handler** that redirects to the web index

### Side Effects on Import

When `modules/utils/queue_worker.py` is imported, it immediately:
- Starts the background worker thread as a daemon
- Initializes the `UsageRepository` with a batch size of 1000

This happens once per process (per Gunicorn worker).

## Request Lifecycle

### 1. Authentication (before_request)

For API blueprints, `require_api_key()` runs before every request:

```
Request arrives
    |
    +--> Is endpoint @public_endpoint? --> Skip auth
    |
    +--> Extract token from Authorization or X-API-Key header
    |
    +--> SHA-256 hash the token
    |
    +--> Look up hash in api_keys collection
    |         |
    |         +--> Not found or revoked --> 403
    |
    +--> Store g.owner, g.scopes, g.api_key_hash, g.is_mod_key
    |
    +--> If mod key: check endpoint in _mod_allowed_endpoints
              |
              +--> Not whitelisted --> 403
```

### 2. Scope Check (decorator)

Endpoints decorated with `@require_scope('scope:name')` verify the required scope is in `g.scopes`. The mod key bypasses scope checks if the endpoint is `@mod_allowed`.

### 3. Business Logic

The route handler delegates to the service layer, which validates data and either:
- **Reads**: queries the repository layer directly and returns results
- **Writes**: enqueues a `CollectionRequest` for background processing

### 4. Usage Recording (after_request)

`record_api_usage()` enqueues a usage record for every authenticated request. The `UsageRepository` buffers these in memory and flushes to MongoDB in batches of 1000.

## Shutdown

### Graceful Shutdown

When a Gunicorn worker exits, `gunicorn_config.py`'s `worker_exit()` hook calls `shutdown_workers()`:

1. Sends a `None` sentinel to the queue to signal the worker thread to stop
2. Waits up to 60 seconds for the worker thread to drain remaining items
3. Flushes any remaining buffered API usage counts to MongoDB

```python
def shutdown_workers():
    _request_queue.put(None)        # Signal worker to stop
    _worker_thread.join(timeout=60) # Wait for drain
    _usage_repo.flush_all()         # Persist remaining counters
```

This ensures no data is lost during deployments or worker recycling.
