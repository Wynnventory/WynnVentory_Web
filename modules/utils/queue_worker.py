import logging
from logging import StreamHandler, Formatter

# ─── BOOTSTRAP ROOT LOGGER ─────────────────────────────────────────────────────
root = logging.getLogger()
root.setLevel(logging.INFO)

# only add our handler once, to avoid duplicates on reload
if not any(isinstance(h, StreamHandler) for h in root.handlers):
    handler = StreamHandler()  # defaults to stderr, Heroku will capture
    handler.setLevel(logging.INFO)
    handler.setFormatter(
        Formatter("%(asctime)s %(levelname)-8s worker %(process)d: %(message)s")
    )
    root.addHandler(handler)

# ─── MODULE LOGGER ─────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)

from queue import Queue
from threading import Thread
import traceback

from modules.models.collection_types import Collection
from modules.repositories import market_repo, lootpool_repo, raidpool_repo
from modules.repositories.usage_repo import UsageRepository

# ─── INTERNAL QUEUE & REPO MAPPING ─────────────────────────────────────────────
_request_queue = Queue()

_usage_repo = UsageRepository()

# ─── WORKER LOOP ────────────────────────────────────────────────────────────────
def _worker_loop():
    """
    Main worker loop that processes items from the queue.
    Runs in a separate thread and continues until shutdown is signaled.
    """
    logger.info("Worker loop started")
    while True:
        try:
            # Get the next item from the queue (blocking operation)
            collection_type, item = _request_queue.get()
            queue_size = _request_queue.qsize()

            # Check if this is a shutdown signal
            if item is None:
                _request_queue.task_done()
                logger.info(f"Worker for {collection_type} shutting down, {queue_size} items remaining in queue")
                break

            # Log the item being processed
            if collection_type:
                logger.info(f"Processing {collection_type.name} item, queue size: {queue_size}")
            else:
                logger.info(f"Processing item with unknown collection type, queue size: {queue_size}")

            # Process the item based on its collection type
            try:
                if collection_type == Collection.MARKET:
                    market_repo.save(item)
                    logger.info(f"Successfully saved MARKET item")
                elif collection_type == Collection.LOOT:
                    lootpool_repo.save(item)
                    logger.info(f"Successfully saved LOOT item")
                elif collection_type == Collection.RAID:
                    raidpool_repo.save(item)
                    logger.info(f"Successfully saved RAID item")
                elif collection_type == Collection.API_USAGE:
                    _usage_repo.save(item)
                    logger.info(f"Successfully saved API_USAGE item")
                else:
                    logger.error(f"No repository configured for {collection_type!r}")
            except Exception as e:
                logger.error(f"Error processing {collection_type} item: {str(e)}")
                # We still mark the task as done even if it failed
                # This prevents the queue from getting stuck

            # Mark the task as done
            _request_queue.task_done()

        except Exception as e:
            # Catch any exceptions in the worker loop itself to prevent thread termination
            logger.error(f"Unexpected error in worker loop: {str(e)}")
            logger.info(f"Error details: {traceback.format_exc()}")
            # Don't call task_done() here as we didn't get an item from the queue


# ─── START UP WORKERS ──────────────────────────────────────────────────────────
_worker_thread = Thread(target=_worker_loop, daemon=True)
_worker_thread.start()
logger.info("Background queue worker started")


# ─── PUBLIC API ────────────────────────────────────────────────────────────────
def enqueue(collection_type: Collection, item: dict):
    """
    Add an item to the processing queue for the specified collection type.

    Args:
        collection_type: The type of collection (MARKET, LOOT, RAID, API_USAGE)
        item: The data to be saved
    """
    _request_queue.put((collection_type, item))
    queue_size = _request_queue.qsize()
    logger.info(f"Enqueued item for {collection_type.name}, queue size: {queue_size}")


def shutdown_workers():
    """
    Gracefully shut down the worker thread and ensure all data is saved.

    Process:
    1) Signal the worker loop to exit after it drains the queue.
    2) Wait for it to finish processing all enqueued items.
    3) Flush any buffered repos (e.g. UsageRepository).

    Returns:
        bool: True if shutdown completed successfully, False otherwise
    """
    try:
        queue_size = _request_queue.qsize()
        logger.info(f"shutdown_workers() called, stopping worker thread with {queue_size} items in queue")

        # 1) tell the worker to stop once it's picked up everything
        _request_queue.put((None, None))
        logger.info("Shutdown signal added to queue")

        # 2) wait for the worker to drain the queue and exit
        logger.info("Waiting for worker thread to complete processing remaining items")
        _worker_thread.join(timeout=60)  # Add timeout to prevent hanging indefinitely

        if _worker_thread.is_alive():
            logger.error("Worker thread did not exit within timeout period")
            return False

        logger.info("Worker thread has exited successfully")

        # 3) now flush any in‑memory buffers
        logger.info("Flushing in-memory buffers")
        _usage_repo.flush_all()

        logger.info("All queue workers have shut down and buffers flushed")
        return True

    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
        logger.info(f"Error details: {traceback.format_exc()}")
        return False
