from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import logging

# MongoDB connection settings
MONGO_URI = "mongodb+srv://Test1234:Test1234@wynnventory.9axarep.mongodb.net/?retryWrites=true&w=majority&appName=wynnventory"
DB_NAME = "wynnventory"
ORIGINAL_COLLECTION = "trademarket_items_DEV"
SUMMARY_COLLECTION = "tm_items_ARCH_DEV"
DAY_OFFSET = 7

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

def archive_and_summarize():
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    from_day = today - timedelta(days=DAY_OFFSET)
    to_day = today - timedelta(days=DAY_OFFSET + 1)

    logging.info(f"Archiving data from {to_day.isoformat()} to {from_day.isoformat()}")

    # Aggregation pipeline
    pipeline = [
        {"$match": {
            "timestamp": {"$gte": to_day, "$lt": from_day},
            "shiny_stat": {"$eq": None}
        }},
        {"$group": {
            "_id": "$name",
            # Identified items
            "minPrice": {"$min": {
                "$cond": [
                    {"$eq": ["$unidentified", False]},
                    "$listing_price",
                    None
                ]
            }},
            "maxPrice": {"$max": {
                "$cond": [
                    {"$eq": ["$unidentified", False]},
                    "$listing_price",
                    None
                ]
            }},
            "sumPrice": {"$sum": {
                "$cond": [
                    {"$eq": ["$unidentified", False]},
                    "$listing_price",
                    0
                ]
            }},
            "countPrice": {"$sum": {
                "$cond": [
                    {"$eq": ["$unidentified", False]},
                    1,
                    0
                ]
            }},
            "prices": {"$push": {
                "$cond": [
                    {"$eq": ["$unidentified", False]},
                    "$listing_price",
                    None
                ]
            }},
            # Unidentified items
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
            # Total counts
            "totalCount": {"$sum": 1},
            "unidentifiedCount": {"$sum": {
                "$cond": [
                    {"$eq": ["$unidentified", True]},
                    1,
                    0
                ]
            }}
        }},
        # Filter out None values from prices arrays
        {"$project": {
            "_id": 0,
            "name": "$_id",
            "minPrice": 1,
            "maxPrice": 1,
            "sumPrice": 1,
            "countPrice": 1,
            "prices": {
                "$filter": {
                    "input": "$prices",
                    "as": "price",
                    "cond": {"$ne": ["$$price", None]}
                }
            },
            "sumUnidentifiedPrice": 1,
            "countUnidentified": 1,
            "unidentifiedPrices": {
                "$filter": {
                    "input": "$unidentifiedPrices",
                    "as": "price",
                    "cond": {"$ne": ["$$price", None]}
                }
            },
            "totalCount": 1,
            "unidentifiedCount": 1
        }},
        # Sort the prices arrays
        {"$project": {
            "name": 1,
            "lowest_price": {"$round": ["$minPrice", 2]},
            "highest_price": {"$round": ["$maxPrice", 2]},
            "average_price": {"$round": [
                {"$cond": [{"$gt": ["$countPrice", 0]}, {"$divide": ["$sumPrice", "$countPrice"]}, None]},
                2
            ]},
            "prices": {"$sortArray": {"input": "$prices", "sortBy": 1}},
            "unidentified_average_price": {"$round": [
                {"$cond": [{"$gt": ["$countUnidentified", 0]}, {"$divide": ["$sumUnidentifiedPrice", "$countUnidentified"]}, None]},
                2
            ]},
            "unidentifiedPrices": {"$sortArray": {"input": "$unidentifiedPrices", "sortBy": 1}},
            "total_count": "$totalCount",
            "unidentified_count": "$unidentifiedCount"
        }},
        # Calculate mid 80% averages with adjusted slicing logic
        {"$project": {
            "name": 1,
            "lowest_price": 1,
            "highest_price": 1,
            "average_price": 1,
            # Average of middle 80% for identified items
            "average_mid_80_percent_price": {
                "$round": [
                    {
                        "$cond": [
                            {"$gte": [{"$size": "$prices"}, 2]},
                            {"$avg": {
                                "$slice": [
                                    "$prices",
                                    {"$ceil": {"$multiply": [{"$size": "$prices"}, 0.1]}},
                                    {
                                        "$max": [
                                            1,
                                            {"$subtract": [
                                                {"$floor": {"$multiply": [{"$size": "$prices"}, 0.9]}},
                                                {"$ceil": {"$multiply": [{"$size": "$prices"}, 0.1]}}
                                            ]}
                                        ]
                                    }
                                ]
                            }},
                            {"$avg": "$prices"}
                        ]
                    }, 2
                ]
            },
            "unidentified_average_price": 1,
            # Average of middle 80% for unidentified items
            "unidentified_average_mid_80_percent_price": {
                "$round": [
                    {
                        "$cond": [
                            {"$gte": [{"$size": "$unidentifiedPrices"}, 2]},
                            {"$avg": {
                                "$slice": [
                                    "$unidentifiedPrices",
                                    {"$ceil": {"$multiply": [{"$size": "$unidentifiedPrices"}, 0.1]}},
                                    {
                                        "$max": [
                                            1,
                                            {"$subtract": [
                                                {"$floor": {"$multiply": [{"$size": "$unidentifiedPrices"}, 0.9]}},
                                                {"$ceil": {"$multiply": [{"$size": "$unidentifiedPrices"}, 0.1]}}
                                            ]}
                                        ]
                                    }
                                ]
                            }},
                            {"$avg": "$unidentifiedPrices"}
                        ]
                    }, 2
                ]
            },
            "total_count": 1,
            "unidentified_count": 1
        }}
    ]

    summaries = list(db[ORIGINAL_COLLECTION].aggregate(pipeline, allowDiskUse=True))

    if not summaries:
        logging.info("No data to archive.")
        return

    for summary in summaries:
        summary["date"] = from_day

    logging.info(f"Found {len(summaries)} unique items to archive and summarize.")

    # Insert summaries into the archive collection
    db[SUMMARY_COLLECTION].insert_many(summaries)

    logging.info("Summarization complete. Archiving original data.")

    # Delete the original data in the date range
    db[ORIGINAL_COLLECTION].delete_many({
        "timestamp": {
            "$gte": to_day,
            "$lt": from_day
        }
    })
    logging.info(f"Original data older than {DAY_OFFSET} days deleted. Archiving process complete.")

if __name__ == "__main__":
    archive_and_summarize()
