"""
migrate_archives.py

Normalize and consolidate MARKET_ARCHIVE so that for each (name, tier, timestamp),
there is at most one document with shiny=True and one with shiny=False.

We break the consolidation into per‐timestamp batches to avoid exceeding MongoDB’s
100 MB in-RAM limit on large $group stages.
"""

import logging
import sys
from datetime import datetime, timezone

from jobs.archive_tm_items import archive_and_summarize
from modules.db import get_collection
from modules.models.collection_types import Collection
from modules.repositories.market_repo import update_moving_averages_complete

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def migrate_existing_and_consolidate():
    try:
        coll = get_collection(Collection.MARKET_ARCHIVE)
    except Exception as e:
        logging.error(f"Error connecting to MongoDB: {e}")
        sys.exit(1)

    # STEP 1: Normalize fields on all existing documents in one go.
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

    # STEP 2: Gather each distinct timestamp value still in the collection.
    # (These are the “date” values we migrated → “timestamp” above.)
    distinct_timestamps = coll.distinct("timestamp")
    logging.info(f"Found {len(distinct_timestamps)} distinct timestamp(s) to consolidate.")

    # STEP 3: For each timestamp, run a small aggregation that groups by (name, tier, shiny, timestamp).
    # At most two output documents per (name, tier, timestamp) batch: shiny=true and shiny=false.
    #
    # This avoids the “Exceeded memory limit” issue by only grouping that single date's documents at a time.
    for ts in distinct_timestamps:
        logging.info(f"Consolidating documents for timestamp {ts.isoformat()} ...")

        # 3a) Filter to only docs with this exact timestamp.
        # 3b) Group them by (name, tier, shiny, timestamp) and merge numeric fields.
        batch_pipeline = [
            {"$match": {"timestamp": ts}},

            {
                "$group": {
                    "_id": {
                        "name": "$name",
                        "tier": "$tier",
                        "shiny": "$shiny",
                        "timestamp": "$timestamp"
                    },
                    # Numeric extremes:
                    "lowest_price": {"$min": "$lowest_price"},
                    "highest_price": {"$max": "$highest_price"},
                    # Sum counts:
                    "total_count": {"$sum": "$total_count"},
                    "unidentified_count": {"$sum": "$unidentified_count"},
                    # Weighted sums for recomputing averages:
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
                    # Metadata — take any one:
                    "item_type": {"$first": "$item_type"},
                    "icon": {"$first": "$icon"}
                }
            },
            {
                "$project": {
                    # Unpack the grouping key:
                    "name": "$_id.name",
                    "tier": "$_id.tier",
                    "shiny": "$_id.shiny",
                    "timestamp": "$_id.timestamp",
                    "item_type": 1,
                    "icon": 1,

                    # Extremes & counts:
                    "lowest_price": 1,
                    "highest_price": 1,
                    "total_count": 1,
                    "unidentified_count": 1,

                    # Recompute weighted averages (round to 2 decimal places):
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

        # Run this small aggregation, allowing disk if needed (though each timestamp is hopefully small enough):
        merged_batch = list(coll.aggregate(batch_pipeline, allowDiskUse=True))
        logging.info(f"  → {len(merged_batch)} consolidated doc(s) for {ts.isoformat()}.")

        # Step 3b: Remove all old docs for this timestamp from the collection,
        # and then insert the newly merged ones.
        del_result = coll.delete_many({"timestamp": ts})
        logging.info(f"  Deleted {del_result.deleted_count} old doc(s) with timestamp {ts.isoformat()}.")

        if merged_batch:
            # Remove any leftover "_id" fields before inserting
            for d in merged_batch:
                d.pop("_id", None)
            ins_result = coll.insert_many(merged_batch)
            logging.info(f"  Inserted {len(ins_result.inserted_ids)} merged doc(s) for {ts.isoformat()}.")
        else:
            logging.info(f"  No merged docs to re‐insert for {ts.isoformat()}.")

    logging.info("Finished normalizing + consolidating MARKET_ARCHIVE.")


if __name__ == "__main__":
    logging.info("Starting migration: normalize & consolidate MARKET_ARCHIVE…")
    migrate_existing_and_consolidate()

    # Initial Averages
    start = datetime(2025, 5, 25, tzinfo=timezone.utc)
    end   = datetime(2025, 5, 26, tzinfo=timezone.utc)

    print(f"Updating initial averages from {start} to {end}")
    update_moving_averages_complete(force_update=True, start_date=start, end_date=end)

    logging.info("Archiving previous week's TM items…")
    for i in range(7, -1, -1):
        logging.info(f"Archiving TM items from {i} days ago…")
        archive_and_summarize(offset=i, force_update=True)
