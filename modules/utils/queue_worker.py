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
from modules.models.collection_request import CollectionRequest
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
    while True:
        try:
            # Get the next item from the queue (blocking operation)
            request = _request_queue.get()
            queue_size = _request_queue.qsize()

            # Check if this is a shutdown signal
            if request is None:
                _request_queue.task_done()
                logger.info(f"Worker is shutting down, {queue_size} items remaining in queue")
                break

            collection_type = request.type
            if collection_type is not None:
                if collection_type != Collection.API_USAGE:
                    logger.info(f"Processing {collection_type.name} item, queue size: {queue_size}, items in request: {len(request.items)}")
            else:
                logger.warning(f"Processing item with unknown collection type, queue size: {queue_size}. Skipping request")
                _request_queue.task_done()
                continue

        # Process the item based on its collection type
            try:
                items_to_process = request.items

                if items_to_process:
                    if collection_type == Collection.MARKET_LISTINGS:
                        market_repo.save(items_to_process)
                    elif collection_type == Collection.LOOT:
                        lootpool_repo.save(items_to_process)
                    elif collection_type == Collection.RAID:
                        raidpool_repo.save(items_to_process)
                    elif collection_type == Collection.GAMBIT:
                        raidpool_repo.save_gambits(items_to_process)
                    elif collection_type == Collection.API_USAGE:
                        _usage_repo.save(items_to_process)
                    else:
                        logger.error(f"No repository configured for {collection_type!r}")
                else:
                    logger.warning(f"No items were passed in request {request}")
                    _request_queue.task_done()
                    continue

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
logger.info("Queue worker started")


# ─── PUBLIC API ────────────────────────────────────────────────────────────────
def enqueue(request: CollectionRequest):
    """
    Add a collection of items to the processing queue for the specified collection type.

    Args:
        request (CollectionRequest): A CollectionRequest object containing:
            - type: The type of collection (MARKET, LOOT, RAID, API_USAGE)
            - items: A list of items to be processed
    """
    _request_queue.put(request)


def shutdown_workers():
    """
    Gracefully shut down the worker thread and ensure all data is saved.
    """
    try:
        queue_size = _request_queue.qsize()
        logger.info(f"shutdown_workers() called, stopping worker thread with {queue_size} items in queue")

        # 1) tell the worker to stop once it's picked up everything
        _request_queue.put(None)  # <-- send a single None, not a tuple
        logger.info("Shutdown signal added to queue")

        # 2) wait for the worker to drain the queue and exit
        logger.info("Waiting for worker thread to complete processing remaining items")
        _worker_thread.join(timeout=60)

        if _worker_thread.is_alive():
            logger.error("Worker thread did not exit within timeout period")
            return False

        logger.info("Worker thread has exited successfully")

        # 3) now flush any in-memory buffers
        logger.info("Flushing in-memory buffers")
        _usage_repo.flush_all()

        logger.info("All queue workers have shut down and buffers flushed")
        return True

    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
        logger.info(f"Error details: {traceback.format_exc()}")
        return False
