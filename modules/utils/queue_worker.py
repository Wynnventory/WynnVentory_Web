import logging
from queue import Queue
from threading import Thread

from modules.models.collection_types import Collection
from modules.repositories.lootpool_repo import LootpoolRepository
from modules.repositories.market_repo import MarketRepository
from modules.repositories.raidpool_repo import RaidpoolRepository
from modules.repositories.usage_repo import UsageRepository

# ─── INTERNAL QUEUE & REPO MAPPING ─────────────────────────────────────────────

_request_queue = Queue()
_repo_map = {
    Collection.MARKET: MarketRepository(),
    Collection.LOOT: LootpoolRepository(),
    Collection.RAID: RaidpoolRepository(),
    Collection.API_USAGE: UsageRepository()
}


# ─── WORKER LOOP ────────────────────────────────────────────────────────────────

def _worker_loop():
    while True:
        collection_type, item = _request_queue.get()
        # Sentinel for clean shutdown
        if item is None:
            _request_queue.task_done()
            logging.info(f"Worker for {collection_type} shutting down")
            break

        repo = _repo_map.get(collection_type)
        if not repo:
            logging.error(f"No repository configured for {collection_type!r}")
        else:
            try:
                repo.save(item)
                logging.debug(f"Saved item to {collection_type}")
            except Exception as e:
                logging.exception(f"Error saving to {collection_type}: {e}")
            finally:
                _request_queue.task_done()


# ─── START UP WORKERS ──────────────────────────────────────────────────────────

# You can start more threads here if you want parallelism:
_worker_thread = Thread(target=_worker_loop, daemon=True)
_worker_thread.start()
logging.info("Background queue worker started")


# ─── PUBLIC API ────────────────────────────────────────────────────────────────

def enqueue(collection_type: Collection, item: dict):
    """
    Queue up an item for asynchronous saving.

    :param collection_type: one of Collection.MARKET, .LOOT, .RAID
    :param item: formatted dict ready for insertion
    """
    _request_queue.put((collection_type, item))


def shutdown_workers():
    """
    Gracefully stop all worker threads by enqueuing a sentinel per thread.
    Call this at app shutdown.
    """
    # If you have N threads, enqueue N sentinels. Here we only have one:
    print("WORKER JUST GOT KILLED")
    _request_queue.put((None, None))
    _worker_thread.join()
    logging.info("All queue workers have shut down")
    _repo_map.get(Collection.API_USAGE).flush_all()
