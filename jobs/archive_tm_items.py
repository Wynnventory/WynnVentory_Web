import logging
from datetime import datetime, timedelta, timezone

from pymongo import InsertOne

from modules.db import get_collection
from modules.models.collection_types import Collection
from modules.repositories.market_repo import update_moving_averages_complete

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def archive_and_summarize(offset: int = 0, force_update: bool = False):
    listings_collection = get_collection(Collection.MARKET_LISTINGS)
    averages_collection = get_collection(Collection.MARKET_AVERAGES)
    archive_collection = get_collection(Collection.MARKET_ARCHIVE)

    # Define the window: documents where "timestamp" is >= start_date and < end_date
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = today - timedelta(days=offset + 1)
    end_date = today - timedelta(days=offset)

    logging.info(f"Archiving MARKET_AVERAGES docs from {start_date.isoformat()} to {end_date.isoformat()}")

    # 1) COPY matching docs from MARKET_AVERAGES → MARKET_ARCHIVE, updating their timestamp to now
    cursor = averages_collection.find({})

    ops = []
    for doc in cursor:
        doc.pop("_id", None)  # remove existing _id so Mongo generates a new one
        doc["timestamp"] = start_date  # update timestamp
        ops.append(InsertOne(doc))

    if ops:
        archive_collection.bulk_write(ops, ordered=False)
        logging.info(f"Inserted {len(ops)} documents into MARKET_ARCHIVE with updated timestamps.")
    else:
        logging.info("No MARKET_AVERAGES documents found for that date range; nothing to archive.")
        return

    # 2) DELETE from MARKET_LISTINGS all docs whose timestamp is in the same range
    delete_result = listings_collection.delete_many({
        "timestamp": {"$gte": start_date, "$lt": end_date}
    })

    logging.info(f"Deleted {delete_result.deleted_count} MARKET_LISTINGS docs older than {offset} days.")

    # 3) Recompute moving averages for all remaining items
    calc_start = start_date + timedelta(days=1)
    calc_end = end_date + timedelta(days=1)
    logging.info(
        f"Recalculating moving averages for all items between {calc_start.isoformat()} and {calc_end.isoformat()}")
    update_moving_averages_complete(force_update=force_update, start_date=calc_start, end_date=calc_end)
    logging.info("Recalculation complete. Archive job finished.")


if __name__ == "__main__":
    archive_and_summarize()
