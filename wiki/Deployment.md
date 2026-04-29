# Deployment

**Sources:** `Procfile`, `modules/gunicorn_config.py`, `jobs/archive_tm_items.py`, `app.py`

## Production (Heroku + Gunicorn)

### Process Configuration

The `Procfile` defines a single web dyno:

```
web: gunicorn 'modules:create_app()' -c modules/gunicorn_config.py -w 10
```

### Gunicorn Settings

**Source:** `modules/gunicorn_config.py`

| Setting | Value | Purpose |
|---------|-------|---------|
| Workers | 10 | Concurrent request handling |
| Log level | INFO | Operational visibility |
| Error log | stdout (`"-"`) | Heroku log drain |
| Access log | stdout (`"-"`) | Heroku log drain |
| `worker_exit` hook | `shutdown_workers()` | Graceful queue/buffer shutdown |

### Worker Isolation

Each of the 10 Gunicorn workers is an independent process with its own:
- Flask application instance
- MongoDB connection pool (max 50 connections)
- Background queue worker thread
- Wynncraft API in-memory cache
- API usage buffer

Total maximum MongoDB connections: 10 workers x 50 pool size = 500 connections (across two databases).

### Worker Exit Hook

When a worker exits (due to recycling, scaling, or deployment):

```python
def worker_exit(server, worker):
    from modules.utils.queue_worker import shutdown_workers
    shutdown_workers()
```

This ensures:
1. Remaining queue items are processed
2. Buffered API usage counts are flushed to MongoDB
3. No data is lost during deployments

## Development Mode

```python
# app.py
app.run(
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 5000)),
    debug=(Config.ENVIRONMENT != "prod")
)
```

- Port: 5000 (default) or `PORT` env var
- Debug mode: enabled when `ENVIRONMENT != "prod"`
- Single process, single thread (Flask dev server)
- Static file caching: `SEND_FILE_MAX_AGE_DEFAULT = 31536000` (1 year)
- Compact JSON: `JSON_SORT_KEYS = False`

## Nightly Archive Job

**Source:** `jobs/archive_tm_items.py`

The archive job is designed to be run once per day by an external scheduler (e.g., Heroku Scheduler). It is NOT a continuously running process.

### Execution

```bash
python -m jobs.archive_tm_items
```

Or called directly:

```python
archive_and_summarize(offset=0, force_update=False)
```

### What It Does

Given `offset=0` (default, meaning "yesterday"):

1. **Define window:**
   - `start_date` = yesterday midnight UTC
   - `end_date` = today midnight UTC

2. **Archive:** Copy all `MARKET_AVERAGES` documents into `MARKET_ARCHIVE` with `timestamp = start_date`
   - Uses `bulk_write()` with `InsertOne` operations
   - Removes `_id` from source documents so MongoDB generates new ones

3. **Cleanup:** Delete `MARKET_LISTINGS` documents with timestamps in `[start_date, end_date)`
   - Removes listings that have been summarized into the archive

4. **Recalculate:** Call `update_moving_averages_complete()` for remaining listings
   - Date window: `[start_date + 1 day, end_date + 1 day)`
   - This advances the EMA by one day using the newly created archive entry as the prior

### Offset Parameter

The `offset` parameter shifts the archive window backwards:
- `offset=0` -- archives yesterday's data (default)
- `offset=1` -- archives the day before yesterday
- Useful for backfilling missed days

### force_update Parameter

When `True`, bypasses the staleness check in `update_moving_averages()` and recalculates all items regardless of whether their listings have changed.

## Environment Variables

See [Configuration](Configuration.md) for the complete list.

## Dependencies

Core Python dependencies (from `requirements.txt`):

| Package | Purpose |
|---------|---------|
| Flask | Web framework |
| gunicorn | WSGI server |
| pymongo | MongoDB driver |
| requests | HTTP client (Wynncraft API) |
| python-decouple | Environment variable management |
| pydantic | Request validation |
