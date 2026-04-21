# Queue Worker

**Source:** `modules/utils/queue_worker.py`

## Overview

The queue worker is a single background daemon thread that processes all write operations asynchronously. It decouples HTTP request handling from database writes, ensuring fast response times for the API.

## Architecture

```
HTTP Handler
     |
     | enqueue(CollectionRequest)
     v
+------------------+
|  _request_queue  |  Thread-safe Queue (unlimited)
+------------------+
     |
     | _worker_loop() [daemon thread]
     v
+------------------+
|   Repository     |  market_repo, lootpool_repo, raidpool_repo, usage_repo
+------------------+
     |
     v
+------------------+
|    MongoDB       |
+------------------+
```

## CollectionRequest

The queue accepts `CollectionRequest` objects (`modules/models/collection_request.py`):

```python
class CollectionRequest:
    type: Collection  # Which collection to write to
    items: list       # List of documents to process
```

## Dispatch Table

The worker dispatches to the appropriate repository based on the collection type:

| Collection Type | Repository Call |
|----------------|----------------|
| `MARKET_LISTINGS` | `market_repo.save(items)` |
| `LOOT` | `lootpool_repo.save(items)` |
| `RAID` | `raidpool_repo.save(items)` |
| `GAMBIT` | `raidpool_repo.save_gambits(items)` |
| `API_USAGE` | `_usage_repo.save(items)` |

## Worker Loop

The worker runs in an infinite loop:

```python
while True:
    request = _request_queue.get()  # Blocks until item available

    if request is None:             # Shutdown sentinel
        break

    # Dispatch to appropriate repository
    if request.type == Collection.MARKET_LISTINGS:
        market_repo.save(request.items)
    elif request.type == Collection.LOOT:
        lootpool_repo.save(request.items)
    # ... etc

    _request_queue.task_done()
```

Key behaviors:
- **Blocking get** -- the thread sleeps when the queue is empty
- **Error isolation** -- exceptions during processing are logged but don't crash the worker
- **Task tracking** -- `task_done()` is called after every item, even on failure
- **Logging** -- queue size and item counts are logged for each non-usage operation

## Thread Safety

- The `Queue` class is inherently thread-safe
- The worker thread is started as a **daemon** -- it will be killed if the main process exits without explicit shutdown
- Only one worker thread exists per process (per Gunicorn worker)

## Graceful Shutdown

`shutdown_workers()` is called by `gunicorn_config.py`'s `worker_exit()` hook:

```
1. Put None sentinel into queue
   --> Worker processes remaining items, then exits loop

2. Join worker thread (timeout=60s)
   --> Wait for worker to finish

3. Flush usage repository buffers
   --> Persist any remaining in-memory API usage counts
```

If the worker thread doesn't exit within 60 seconds, an error is logged but the process continues shutting down.

## API Usage Buffering

The `UsageRepository` is a special case -- it buffers API usage records in memory to avoid a MongoDB write for every single request:

```python
class UsageRepository:
    batch_size: int = 1000
    _buffer: dict      # key_hash -> count
    _owners: dict      # key_hash -> owner name
    _lock: Lock         # Thread safety
```

- Each incoming record increments a counter in `_buffer`
- When any key's counter reaches `batch_size` (1000), that key is flushed to MongoDB
- On shutdown, `flush_all()` persists all remaining counters
- MongoDB update uses `$inc` for atomic counter increment:

```python
collection.update_one(
    {"key_hash": key},
    {"$inc": {"count": count}, "$setOnInsert": {"owner": owner}},
    upsert=True
)
```

## Startup

The worker thread starts automatically when `queue_worker.py` is imported:

```python
_worker_thread = Thread(target=_worker_loop, daemon=True)
_worker_thread.start()
```

This happens once per process. In production with Gunicorn's 10 workers, there are 10 independent worker threads processing 10 independent queues.
