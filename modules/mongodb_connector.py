from datetime import datetime
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from flask import jsonify

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
    """ Retrieve items from the trademarket collection by name
    """
    collection = db["trademarket_TEST"]

    result = collection.find(
        filter={'name': item_name},
        projection={'_id': 0}
    )

    return check_results(result, custom_message="No items found with that name")


def get_trade_market_item_price(item_name):
    """ Retrieve price of item from the trademarket collection
    """
    collection = db["trademarket_TEST"]

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
                    ]
                }
            },
            {
                "$project": {
                    "lowest_price": {"$arrayElemAt": ["$identified_prices.minPrice", 0]},
                    "highest_price": {"$arrayElemAt": ["$identified_prices.maxPrice", 0]},
                    "average_price": {"$arrayElemAt": ["$identified_prices.avgPrice", 0]},
                    "unidentified_average_price": {"$arrayElemAt": ["$unidentified_avg_price.avgUnidentifiedPrice", 0]}
                }
            }
        ]
    )
    return check_results(result)


def check_results(result, custom_message="No items found"):
    """ Check if the result is empty and return a custom message
    """
    result = list(result)
    if result == [] or result == [{}]:
        return jsonify({"message": custom_message}), 204
    return jsonify(result), 200
