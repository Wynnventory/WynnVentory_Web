"""
migrate_archives.py

Normalize and consolidate MARKET_ARCHIVE so that for each (name, tier, timestamp),
there is at most one document with shiny=True and one with shiny=False.
"""

import logging
import sys

from jobs.archive_tm_items import archive_and_summarize
from modules.db import get_collection
from modules.models.collection_types import Collection
from modules.repositories.market_repo import update_moving_averages_complete

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def migrate_existing_and_consolidate():
    try:
        coll = get_collection(Collection.MARKET_ARCHIVE)
    except Exception as e:
        logging.error(f"Error connecting to MongoDB: {e}")
        sys.exit(1)

    # Step 1: Normalize fields on all existing documents
    normalize_pipeline = [
        # 1) Add “shiny” = (shiny_stat != null)
        {"$set": {"shiny": {"$ne": ["$shiny_stat", None]}}},
        # 2) Copy “date” → “timestamp”
        {"$set": {"timestamp": "$date"}},
        # 3) Remove “shiny_stat” and “date”
        {"$unset": ["shiny_stat", "date"]}
    ]
    res_norm = coll.update_many({}, normalize_pipeline)
    logging.info(f"Normalization: matched={res_norm.matched_count}, modified={res_norm.modified_count}")

    # Step 2: Consolidate per (name, tier, shiny, timestamp)
    # Group any docs that share name/tier/timestamp/shiny into one,
    # merging their numeric fields:
    #
    #   - lowest_price = min(lowest_price)
    #   - highest_price = max(highest_price)
    #   - total_count = sum(total_count)
    #   - unidentified_count = sum(unidentified_count)
    #   - average_price = weighted avg across group: sum(avg_price * total_count) / sum(total_count)
    #   - unidentified_average_price = same, if unidentified_count > 0
    #   - average_mid_80_percent_price = weighted avg: sum(mid80 * total_count) / sum(total_count)
    #   - unidentified_average_mid_80_percent_price = weighted avg: sum(unid_mid80 * unid_count) / sum(unid_count)
    #   - item_type, icon: take any via $first
    consolidate_pipeline = [
        {
            "$group": {
                "_id": {
                    "name": "$name",
                    "tier": "$tier",
                    "shiny": "$shiny",
                    "timestamp": "$timestamp"
                },
                # Numeric extremes
                "lowest_price": {"$min": "$lowest_price"},
                "highest_price": {"$max": "$highest_price"},
                # Sum counts
                "total_count": {"$sum": "$total_count"},
                "unidentified_count": {"$sum": "$unidentified_count"},
                # Weighted sums for averages
                "sum_avg_price_times_count": {
                    "$sum": {"$multiply": ["$average_price", "$total_count"]}
                },
                "sum_unid_avg_times_count": {
                    "$sum": {
                        "$cond": [
                            {"$gt": ["$unidentified_count", 0]},
                            {"$multiply": ["$unidentified_average_price", "$unidentified_count"]},
                            0
                        ]
                    }
                },
                "sum_mid80_times_count": {
                    "$sum": {"$multiply": ["$average_mid_80_percent_price", "$total_count"]}
                },
                "sum_unid_mid80_times_count": {
                    "$sum": {
                        "$cond": [
                            {"$gt": ["$unidentified_count", 0]},
                            {"$multiply": ["$unidentified_average_mid_80_percent_price", "$unidentified_count"]},
                            0
                        ]
                    }
                },
                # Metadata (unchanged across shiny variants)
                "item_type": {"$first": "$item_type"},
                "icon": {"$first": "$icon"}
            }
        },
        {
            "$project": {
                # Unpack grouping key
                "name": "$_id.name",
                "tier": "$_id.tier",
                "shiny": "$_id.shiny",
                "timestamp": "$_id.timestamp",
                "item_type": 1,
                "icon": 1,
                # Extremes and counts
                "lowest_price": 1,
                "highest_price": 1,
                "total_count": 1,
                "unidentified_count": 1,
                # Recompute weighted averages, rounded
                "average_price": {
                    "$round": [
                        {
                            "$cond": [
                                {"$eq": ["$total_count", 0]},
                                None,
                                {
                                    "$divide": ["$sum_avg_price_times_count", "$total_count"]
                                }
                            ]
                        },
                        2
                    ]
                },
                "unidentified_average_price": {
                    "$round": [
                        {
                            "$cond": [
                                {"$eq": ["$unidentified_count", 0]},
                                None,
                                {
                                    "$divide": ["$sum_unid_avg_times_count", "$unidentified_count"]
                                }
                            ]
                        },
                        2
                    ]
                },
                "average_mid_80_percent_price": {
                    "$round": [
                        {
                            "$cond": [
                                {"$eq": ["$total_count", 0]},
                                None,
                                {
                                    "$divide": ["$sum_mid80_times_count", "$total_count"]
                                }
                            ]
                        },
                        2
                    ]
                },
                "unidentified_average_mid_80_percent_price": {
                    "$round": [
                        {
                            "$cond": [
                                {"$eq": ["$unidentified_count", 0]},
                                None,
                                {
                                    "$divide": ["$sum_unid_mid80_times_count", "$unidentified_count"]
                                }
                            ]
                        },
                        2
                    ]
                }
            }
        }
    ]

    logging.info("Running consolidation aggregation...")
    merged_docs = list(coll.aggregate(consolidate_pipeline, allowDiskUse=True))
    logging.info(f"Consolidation produced {len(merged_docs)} documents.")

    # Step 3: Replace the collection with the merged docs
    delete_result = coll.delete_many({})
    logging.info(f"Deleted {delete_result.deleted_count} old archive documents.")

    if merged_docs:
        for doc in merged_docs:
            doc.pop("_id", None)
        insert_result = coll.insert_many(merged_docs)
        logging.info(f"Inserted {len(insert_result.inserted_ids)} merged documents.")
    else:
        logging.info("No merged documents to insert (collection is now empty).")


if __name__ == "__main__":
    logging.info("Migrating existing archive documents (normalize + consolidate)...")
    migrate_existing_and_consolidate()

    logging.info("Recalculating moving averages on consolidated data...")
    update_moving_averages_complete(True)

    logging.info("Archiving previous week's TM items...")
    for i in range(7, -1, -1):
        logging.info(f"Archiving TM items from {i} days ago...")
        archive_and_summarize(offset=i, force_update=True)
