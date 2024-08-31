from pymongo import MongoClient
from datetime import datetime, timedelta
import logging

# Archive all items of {ORIGINAL_COLLECTION} older than {DAY_OFFSET} days to {SUMMARY_COLLECTION}.
# Before deleting the original data, all items are aggregated to get the min, max, avg price of identified items and avg price of unidentified items.

# MongoDB connection settings
MONGO_URI = "mongodb+srv://Test1234:Test1234@wynnventory.9axarep.mongodb.net/?retryWrites=true&w=majority&appName=wynnventory"
DB_NAME = "wynnventory"
ORIGINAL_COLLECTION = "trademarket_items_PROD"
SUMMARY_COLLECTION = "tm_items_ARCH_PROD"
DAY_OFFSET = 7

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
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    # today = datetime(2024, 8, 25, 0, 0, 0, 0) # Manual date
    from_day = today - timedelta(days=DAY_OFFSET)
    to_day = today - timedelta(days=DAY_OFFSET + 1)

    logging.info(f"Archiving data from {to_day.isoformat()} to {from_day.isoformat()}")

    # Get distinct item names for the data older than 3 days
    item_names = db[ORIGINAL_COLLECTION].distinct("name", {
        "timestamp": {"$gte": to_day, "$lt": from_day}
    })

    if not item_names:
        logging.info("No data to archive.")
        return

    summaries = []
    total_items = len(item_names)
    logging.info(f"Found {total_items} unique items to archive and summarize.")
    for i, item_name in enumerate(item_names, start=1):
        summary = aggregate_item_data(item_name, db[ORIGINAL_COLLECTION])
        summary["name"] = item_name
        summary["date"] = from_day
        summaries.append(summary)

        if i % 50 == 0 or i == total_items:
            logging.info(f"Processed {i}/{total_items} items.")
    
    if summaries:
        db[SUMMARY_COLLECTION].insert_many(summaries)


    logging.info("Summarization complete. Archiving original data.")
    # Delete the original data older in date range
    db[ORIGINAL_COLLECTION].delete_many({
        "timestamp": {
            "$gte": to_day,
            "$lt": from_day
        }
    })
    logging.info(f"Original data older than {DAY_OFFSET} days deleted. Archiving process complete.")

if __name__ == "__main__":
    archive_and_summarize()