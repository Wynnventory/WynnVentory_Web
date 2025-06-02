"""
migrate_archives.py

Adds the following fields to every document in the 'archive' collection:
  - shiny_stat: None
  - tier: None
  - item_type: "GearItem"
"""
import logging
import sys

from jobs.archive_tm_items import archive_and_summarize
from modules.db import get_collection
from modules.models.collection_types import Collection
from modules.repositories.market_repo import update_moving_averages_complete

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Connection details

def migrate_existing():
    try:
        collection = get_collection(Collection.MARKET_ARCHIVE)
    except Exception as e:
        logging.info(f"Error connecting to MongoDB: {e}")
        sys.exit(1)

    # Use an aggregation‐pipeline update (MongoDB 4.2+)
    # 1) Compute "shiny" = (shiny_stat != null)
    # 2) Copy "date" → "timestamp"
    # 3) Remove "shiny_stat" and "date"
    pipeline_update = [
        {
            "$set": {
                "shiny": { "$ne": ["$shiny_stat", None] }
            }
        },
        {
            "$set": {
                "timestamp": "$date"
            }
        },
        {
            "$unset": ["shiny_stat", "date"]
        }
    ]

    result = collection.update_many({}, pipeline_update)

    logging.info(f"Matched {result.matched_count} documents.")
    logging.info(f"Modified {result.modified_count} documents.")


if __name__ == "__main__":
    logging.info("Migrating existing archive documents...")
    migrate_existing()

    logging.info("Creating moving averages...")
    update_moving_averages_complete(True)

    logging.info("Archiving previous week's TM items...")
    # 7, 6, 5, 4, 3, 2, 1, 0
    for i in range(7, -1, -1):
        logging.info(f"Archiving TM items from {i} days ago...")
        archive_and_summarize(offset=i, force_update=True)

