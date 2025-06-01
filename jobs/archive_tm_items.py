from datetime import datetime, timedelta, timezone
import logging

from modules.db import get_collection
from modules.models.collection_types import Collection

# MongoDB connection settings
DAY_OFFSET = 7

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def archive_and_summarize():
    trademarket_collection = get_collection(Collection.MARKET_LISTINGS)
    archive_collection = get_collection(Collection.MARKET_ARCHIVE)

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    from_day = today - timedelta(days=DAY_OFFSET)
    to_day = today - timedelta(days=DAY_OFFSET + 1)

    logging.info(f"Archiving data from {to_day.isoformat()} to {from_day.isoformat()}")

    # Aggregation pipeline
    pipeline = [
        {"$match": {
            "timestamp": {"$gte": to_day, "$lt": from_day},
        }},

        # 2) explode each doc into `amount` copies
        {"$addFields": {
            "amountArr": {"$range": [0, "$amount"]}
        }},
        {"$unwind": "$amountArr"},

        # 3) Group by name, shiny_stat, tier, item_type
        {"$group": {
            "_id": {
                "name": "$name",
                "shiny_stat": "$shiny_stat",
                "tier": "$tier",
                "item_type": "$item_type"
            },
            # Identified items (now includes null and false)
            "minPrice": {"$min": {
                "$cond": [
                    {"$ne": ["$unidentified", True]},
                    "$listing_price",
                    None
                ]
            }},
            "maxPrice": {"$max": {
                "$cond": [
                    {"$ne": ["$unidentified", True]},
                    "$listing_price",
                    None
                ]
            }},
            "sumPrice": {"$sum": {
                "$cond": [
                    {"$ne": ["$unidentified", True]},
                    "$listing_price",
                    0
                ]
            }},
            "countPrice": {"$sum": {
                "$cond": [
                    {"$ne": ["$unidentified", True]},
                    1,
                    0
                ]
            }},
            "prices": {"$push": {
                "$cond": [
                    {"$ne": ["$unidentified", True]},
                    "$listing_price",
                    None
                ]
            }},
            # Unidentified items (only true)
            "sumUnidentifiedPrice": {"$sum": {
                "$cond": [
                    {"$eq": ["$unidentified", True]},
                    "$listing_price",
                    0
                ]
            }},
            "countUnidentified": {"$sum": {
                "$cond": [
                    {"$eq": ["$unidentified", True]},
                    1,
                    0
                ]
            }},
            "unidentifiedPrices": {"$push": {
                "$cond": [
                    {"$eq": ["$unidentified", True]},
                    "$listing_price",
                    None
                ]
            }},
            # Totals
            "totalCount": {"$sum": 1},
            "unidentifiedCount": {"$sum": {
                "$cond": [
                    {"$eq": ["$unidentified", True]},
                    1,
                    0
                ]
            }}
        }},
        # 4) Filter out nulls and pull the group‐key fields out of _id
        {"$project": {
            "_id": 0,
            "name": "$_id.name",
            "shiny_stat": "$_id.shiny_stat",
            "tier": "$_id.tier",
            "item_type": "$_id.item_type",
            "minPrice": 1,
            "maxPrice": 1,
            "sumPrice": 1,
            "countPrice": 1,
            "prices": {
                "$filter": {
                    "input": "$prices",
                    "as": "p",
                    "cond": {"$ne": ["$$p", None]}
                }
            },
            "sumUnidentifiedPrice": 1,
            "countUnidentified": 1,
            "unidentifiedPrices": {
                "$filter": {
                    "input": "$unidentifiedPrices",
                    "as": "p",
                    "cond": {"$ne": ["$$p", None]}
                }
            },
            "totalCount": 1,
            "unidentifiedCount": 1
        }},

        # 5) Compute rounded min/max/averages and sort the arrays
        {"$project": {
            "name": 1,
            "shiny_stat": 1,
            "tier": 1,
            "item_type": 1,
            "lowest_price": {"$round": ["$minPrice", 0]},
            "highest_price": {"$round": ["$maxPrice", 0]},
            "average_price": {"$round": [
                {"$cond": [
                    {"$gt": ["$countPrice", 0]},
                    {"$divide": ["$sumPrice", "$countPrice"]},
                    None
                ]},
                0
            ]},
            "prices": {"$sortArray": {"input": "$prices", "sortBy": 1}},
            "unidentified_average_price": {"$round": [
                {"$cond": [
                    {"$gt": ["$countUnidentified", 0]},
                    {"$divide": ["$sumUnidentifiedPrice", "$countUnidentified"]},
                    None
                ]},
                0
            ]},
            "unidentifiedPrices": {"$sortArray": {"input": "$unidentifiedPrices", "sortBy": 1}},
            "total_count": "$totalCount",
            "unidentified_count": "$unidentifiedCount"
        }},
        # Calculate mid 80% averages with adjusted slicing logic
        {
            "$project": {
                "name": 1,
                "shiny_stat": 1,
                "tier": 1,
                "item_type": 1,
                "lowest_price": 1,
                "highest_price": 1,
                "average_price": 1,
                "unidentified_average_price": 1,
                "average_mid_80_percent_price": {
                    "$round": [
                        {
                            "$cond": [
                                {"$gt": [{"$size": "$prices"}, 2]},
                                {
                                    "$avg": {
                                        "$slice": [
                                            "$prices",
                                            {"$ceil": {"$multiply": [{"$size": "$prices"}, 0.1]}},
                                            {
                                                "$subtract": [
                                                    {"$size": "$prices"},
                                                    {
                                                        "$multiply": [
                                                            {"$ceil": {"$multiply": [{"$size": "$prices"}, 0.1]}},
                                                            2
                                                        ]
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                },
                                {"$avg": "$prices"}
                            ]
                        },
                        0
                    ]
                },
                "unidentified_average_mid_80_percent_price": {
                    "$round": [
                        {
                            "$cond": [
                                {"$gt": [{"$size": "$unidentifiedPrices"}, 2]},
                                {
                                    "$avg": {
                                        "$slice": [
                                            "$unidentifiedPrices",
                                            {"$ceil": {"$multiply": [{"$size": "$unidentifiedPrices"}, 0.1]}},
                                            {
                                                "$subtract": [
                                                    {"$size": "$unidentifiedPrices"},
                                                    {
                                                        "$multiply": [
                                                            {"$ceil": {
                                                                "$multiply": [{"$size": "$unidentifiedPrices"}, 0.1]}},
                                                            2
                                                        ]
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                },
                                {"$avg": "$unidentifiedPrices"}
                            ]
                        },
                        0
                    ]
                },
                "total_count": 1,
                "unidentified_count": 1
            }
        }
    ]

    # run it
    summaries = list(trademarket_collection.aggregate(pipeline, allowDiskUse=True))
    if not summaries:
        logging.info("No data to archive.")
        return

    # tag each with the archive date
    for doc in summaries:
        doc["date"] = from_day

    logging.info(f"Found {len(summaries)} unique groups to archive.")

    # write summaries & delete originals
    archive_collection.insert_many(summaries)
    logging.info("Summaries inserted.")

    trademarket_collection.delete_many({
        "timestamp": {"$gte": to_day, "$lt": from_day}
    })
    logging.info("Original data older than 7 days deleted. Job complete.")


if __name__ == "__main__":
    archive_and_summarize()
