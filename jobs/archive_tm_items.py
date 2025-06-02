from datetime import datetime, timedelta, timezone
import logging

from pymongo import InsertOne

from modules.db import get_collection
from modules.models.collection_types import Collection
from modules.repositories.market_repo import update_moving_averages_complete

# MongoDB connection settings
DAY_OFFSET = 0

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def archive_and_summarize():
    listings_collection = get_collection(Collection.MARKET_LISTINGS)
    averages_collection = get_collection(Collection.MARKET_AVERAGES)
    archive_collection = get_collection(Collection.MARKET_ARCHIVE)

    # Define the window: documents where "timestamp" is >= to_day and < from_day
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    from_day = today - timedelta(days=DAY_OFFSET)
    to_day = today - timedelta(days=DAY_OFFSET + 1)

    logging.info(f"Archiving MARKET_AVERAGES docs from {to_day.isoformat()} to {from_day.isoformat()}")

    # 1) COPY matching docs from MARKET_AVERAGES → MARKET_ARCHIVE, updating their timestamp to now
    cursor = averages_collection.find({})

    ops = []
    for doc in cursor:
        doc.pop("_id", None)             # remove existing _id so Mongo generates a new one
        doc["timestamp"] = to_day        # update timestamp
        ops.append(InsertOne(doc))

    if ops:
        archive_collection.bulk_write(ops, ordered=False)
        logging.info(f"Inserted {len(ops)} documents into MARKET_ARCHIVE with updated timestamps.")
    else:
        logging.info("No MARKET_AVERAGES documents found for that date range; nothing to archive.")
        return

    # 2) DELETE from MARKET_LISTINGS all docs whose timestamp is in the same range
    delete_result = listings_collection.delete_many({
        "timestamp": {"$gte": to_day, "$lt": from_day}
    })

    logging.info(f"Deleted {delete_result.deleted_count} MARKET_LISTINGS docs older than {DAY_OFFSET} days.")

    # 3) Recompute moving averages for all remaining items
    logging.info("Recalculating moving averages for all items...")
    update_moving_averages_complete()
    logging.info("Recalculation complete. Archive job finished.")


if __name__ == "__main__":
    archive_and_summarize()
