import logging
import signal
from queue import Queue
from threading import Thread

from modules.models.collection_types import Collection
from modules.repositories.lootpool_repo import LootpoolRepository
from modules.repositories.market_repo import MarketRepository
from modules.repositories.raidpool_repo import RaidpoolRepository
from modules.repositories.usage_repo import UsageRepository

logger = logging.getLogger(__name__)

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
        if item is None:
            _request_queue.task_done()
            logger.info(f"Worker for {collection_type} shutting down")
            break

        repo = _repo_map.get(collection_type)
        if repo:
            try:
                repo.save(item)
                logger.debug(f"Saved item to {collection_type}")
            except Exception:
                logger.exception(f"Error saving to {collection_type}")
        else:
            logger.error(f"No repository configured for {collection_type!r}")
        _request_queue.task_done()


# ─── START UP WORKERS ──────────────────────────────────────────────────────────
_worker_thread = Thread(target=_worker_loop, daemon=True)
_worker_thread.start()
logger.info("Background queue worker started")


# ─── PUBLIC API ────────────────────────────────────────────────────────────────
def enqueue(collection_type: Collection, item: dict):
    _request_queue.put((collection_type, item))


def shutdown_workers():
    """
    Flush any buffered repos (e.g. UsageRepository), then tell the
    worker loop to exit, and wait for it.
    """
    logger.info("shutdown_workers() called, flushing buffers…")
    # 1) flush any repo that has a flush_all()
    for repo in _repo_map.values():
        flush = getattr(repo, "flush_all", None)
        if callable(flush):
            flush()
    # 2) signal the worker loop to stop
    _request_queue.put((None, None))
    _worker_thread.join()
    logger.info("All queue workers have shut down")


# ─── HOOK SIGTERM (Heroku only) ────────────────────────────────────────────────
signal.signal(signal.SIGTERM, lambda sig, frame: shutdown_workers())
