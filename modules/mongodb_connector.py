from datetime import datetime
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

uri = "mongodb+srv://Test1234:Test1234@wynnventory.9axarep.mongodb.net/?retryWrites=true&w=majority&appName=wynnventory"

# Create a new client and connect to the server with SSL settings
client = MongoClient(uri, server_api=ServerApi(
    '1'), tls=True, tlsAllowInvalidCertificates=True)
db = client["wynnventory"]

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
except Exception as e:
    print("Could not connect to MongoDB!", e)


def save_trade_market_item(item):
    """ Save items to the trademarket collection
    """
    collection = db["trademarket_TEST"]

    # Extract relevant fields to check for duplicates (excluding timestamp)
    item_check = {
        "name": item.get("name"),
        "level": item.get("level"),
        "rarity": item.get("rarity"),
        "powder_slots": item.get("powder_slots"),
        "rerolls": item.get("rerolls"),
        # "required_class": item.get("required_class"),
        "unidentified": item.get("unidentified"),
        "shiny_stat": item.get("shiny_stat"),
        # "perfect": item.get("perfect"),
        # "defective": item.get("defective"),
        "amount": item.get("amount"),
        "overall_percentage": item.get("overall_percentage"),
        "listing_price": item.get("listing_price"),
        "actual_stats_with_percentage": item.get("actual_stats_with_percentage")
    }

    # Check for duplicate items
    duplicate_item = collection.find_one(item_check)
    if duplicate_item:
        return {"message": "Duplicate item found, skipping insertion"}, 200

    # Insert the new item if no duplicate is found
    item['timestamp'] = datetime.utcnow()
    collection.insert_one(item)
    return {"message": "Item saved successfully"}, 200


def get_trade_market_item(item_name):
    """ Retrieve items from the trademarket collection
    """
    collection = db["trademarket_TEST"]

    result = collection.aggregate([
        {
            "$match": {
                "name": item_name
            }
        },
        {
            "$group": {
                "_id": "$name",
                "lowest_price": {"$min": "$listing_price"},
                "highest_price": {"$max": "$listing_price"},
                "average_price": {"$avg": "$listing_price"},
                "unidentified_average_price": {
                    "$avg": {
                        "$cond": [
                            {"$eq": ["$unidentified", True]},
                            "$listing_price",
                            None
                        ]
                    }
                }
            }
        },
        {
            "$project": {
                "_id": 0,
                "name": "Idol",
                "lowest_price": {"$round": ["$lowest_price", 2]},
                "highest_price": {"$round": ["$highest_price", 2]},
                "average_price": {"$round": ["$average_price", 2]},
                "unidentified_average_price": {"$round": ["$unidentified_average_price", 2]}
            }
        }
    ])
    return list(result)
