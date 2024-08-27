from pymongo import MongoClient
from datetime import datetime, timedelta
# import pytz
import logging

# MongoDB connection settings
MONGO_URI = "mongodb+srv://Test1234:Test1234@wynnventory.9axarep.mongodb.net/?retryWrites=true&w=majority&appName=wynnventory"
DB_NAME = "wynnventory"
ORIGINAL_COLLECTION = "trademarket_items_DEV"
SUMMARY_COLLECTION = "trademarket_items_2024_DEV2"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

def aggregate_item_data(item_name, collection):
    result = collection.aggregate(
        [
            {
                "$facet": {
                    "identified_prices": [
                        {
                            "$match": {
                                "name": item_name,
                                "unidentified": False,
                                "shiny_stat": {"$eq": None}
                            }
                        },
                        {
                            "$group": {
                                "_id": None,
                                "minPrice": {"$min": "$listing_price"},
                                "maxPrice": {"$max": "$listing_price"},
                                "avgPrice": {"$avg": "$listing_price"}
                            }
                        },
                        {
                            "$project": {
                                "_id": 0,
                                "minPrice": {"$round": ["$minPrice", 2]},
                                "maxPrice": {"$round": ["$maxPrice", 2]},
                                "avgPrice": {"$round": ["$avgPrice", 2]}
                            }
                        }
                    ],
                    "unidentified_avg_price": [
                        {
                            "$match": {
                                "name": item_name,
                                "unidentified": True
                            }
                        },
                        {
                            "$group": {
                                "_id": None,
                                "avgUnidentifiedPrice": {"$avg": "$listing_price"}
                            }
                        },
                        {
                            "$project": {
                                "_id": 0,
                                "avgUnidentifiedPrice": {"$round": ["$avgUnidentifiedPrice", 2]}
                            }
                        }
                    ],
                    "total_items": [
                        {
                            "$match": {
                                "name": item_name
                            }
                        },
                        {
                            "$group": {
                                "_id": None,
                                "totalCount": {"$sum": 1},
                                "unidentifiedCount": {
                                    "$sum": {
                                        "$cond": {
                                            "if": {"$eq": ["$unidentified", True]},
                                            "then": 1,
                                            "else": 0
                                        }
                                    }
                                }
                            }
                        },
                        {
                            "$project": {
                                "_id": 0,
                                "totalCount": 1,
                                "unidentifiedCount": 1
                            }
                        }
                    ]
                }
            },
            {
                "$project": {
                    "lowest_price": {"$arrayElemAt": ["$identified_prices.minPrice", 0]},
                    "highest_price": {"$arrayElemAt": ["$identified_prices.maxPrice", 0]},
                    "average_price": {"$arrayElemAt": ["$identified_prices.avgPrice", 0]},
                    "unidentified_average_price": {"$arrayElemAt": ["$unidentified_avg_price.avgUnidentifiedPrice", 0]},
                    "total_count": {"$arrayElemAt": ["$total_items.totalCount", 0]},
                    "unidentified_count": {"$arrayElemAt": ["$total_items.unidentifiedCount", 0]}
                }
            }
        ]
    )
    return list(result)[0]

def archive_and_summarize():
    # Get the previous day range with timezone
    today = datetime(2024, 8, 27, 0, 0, 0).replace(second=0, microsecond=0)
    yesterday = today - timedelta(days=1)

    logging.info(f"Archiving data from {yesterday.isoformat()} to {today.isoformat()}")

    # Get distinct item names for the previous day
    item_names = db[ORIGINAL_COLLECTION].distinct("name", {
        "timestamp": {"$gte": yesterday, "$lt": today}
    })

    if not item_names:
        logging.info("No data to archive.")
        return

    for item_name in item_names:
        # logging.info(f"Processing item: {item_name}")
        summary = aggregate_item_data(item_name, db[ORIGINAL_COLLECTION])
        summary["name"] = item_name
        summary["date"] = yesterday

        # logging.info(f"Summary for {item_name}: {summary}")
        db[SUMMARY_COLLECTION].insert_one(summary)

    logging.info("Summarization complete. Archiving original data.")

    # Archive or delete the original data if needed
    # db[ORIGINAL_COLLECTION].delete_many({
    #     "timestamp": {"$gte": yesterday, "$lt": today}
    # })

    logging.info("Original data deleted. Archiving process complete.")

if __name__ == "__main__":
    archive_and_summarize()