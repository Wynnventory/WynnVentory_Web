from datetime import datetime, timedelta
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from flask import jsonify

from modules.utils import get_lootpool_week

uri = "mongodb+srv://Test1234:Test1234@wynnventory.9axarep.mongodb.net/?retryWrites=true&w=majority&appName=wynnventory"
PROD_MARKET_DB = "trademarket_items_PROD"
DEV_MARKET_DB = "trademarket_items_DEV"
PROD_LOOT_DB = "lootpool_items_PROD"
DEV_LOOT_DB = "lootpool_items_DEV"
PROD_RAID_DB = "raidpool_items_PROD"
DEV_RAID_DB = "raidpool_items_DEV"

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


def save_trade_market_item(item, environment="prod"):
    """ Save items to the trademarket collection
    """
    collection = get_collection("trademarket", environment)

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
    collection = db[PROD_MARKET_DB]

    result = collection.find(
        filter={'name': item_name},
        projection={'_id': 0}
    )

    return check_results(result, custom_message="No items found with that name")


def get_trade_market_item_price(item_name, environment="prod"):
    """ Retrieve price of item from the trademarket collection
    """
    collection = get_collection("trademarket", environment)

    result = collection.aggregate(
        [
            {
                "$match": {
                    "name": item_name,
                    "shiny_stat": {"$eq": None}
                }
            },
            {"$sort": {"listing_price": 1}},
            {
                "$facet": {
                    "identified_prices": [
                        {
                            "$match": {
                                "unidentified": False,
                            }
                        },
                        {
                            "$group": {
                                "_id": None,
                                "minPrice": {"$min": "$listing_price"},
                                "maxPrice": {"$max": "$listing_price"},
                                "avgPrice": {"$avg": "$listing_price"},
                                "prices": {"$push": "$listing_price"}
                            }
                        },
                        {
                            "$project": {
                                "_id": 0,
                                "minPrice": {"$round": ["$minPrice", 2]},
                                "maxPrice": {"$round": ["$maxPrice", 2]},
                                "avgPrice": {"$round": ["$avgPrice", 2]},
                                "mid_80_percent": {
                                    "$cond": [
                                        {"$gte": [{"$size": "$prices"}, 2]},
                                        {
                                            "$slice": [
                                                "$prices",
                                                {"$ceil": {"$multiply": [
                                                    {"$size": "$prices"}, 0.1]}},
                                                {"$floor": {"$multiply": [
                                                    {"$size": "$prices"}, 0.8]}}
                                            ]
                                        },
                                        "$prices"  # Use the full prices array if less than 2 entries
                                    ]
                                }
                            }
                        },
                        {
                            "$project": {
                                "minPrice": 1,
                                "maxPrice": 1,
                                "avgPrice": 1,
                                "average_mid_80_percent_price": {
                                    "$round": [{"$avg": "$mid_80_percent"}, 2]
                                }
                            }
                        }
                    ],
                    "unidentified_avg_price": [
                        {
                            "$match": {
                                "unidentified": True
                            }
                        },
                        {
                            "$group": {
                                "_id": None,
                                "avgUnidentifiedPrice": {"$avg": "$listing_price"},
                                "prices": {"$push": "$listing_price"}
                            }
                        },
                        {
                            "$project": {
                                "_id": 0,
                                "avgUnidentifiedPrice": {"$round": ["$avgUnidentifiedPrice", 2]},
                                "mid_80_percent": {
                                    "$cond": [
                                        {"$gte": [{"$size": "$prices"}, 2]},
                                        {
                                            "$slice": [
                                                "$prices",
                                                {"$ceil": {"$multiply": [
                                                    {"$size": "$prices"}, 0.1]}},
                                                {"$floor": {"$multiply": [
                                                    {"$size": "$prices"}, 0.8]}}
                                            ]
                                        },
                                        "$prices"  # Use the full prices array if less than 2 entries
                                    ]
                                }
                            }
                        },
                        {
                            "$project": {
                                "avgUnidentifiedPrice": 1,
                                "average_mid_80_percent_price": {
                                    "$round": [{"$avg": "$mid_80_percent"}, 2]
                                }
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
                    "average_mid_80_percent_price": {"$arrayElemAt": ["$identified_prices.average_mid_80_percent_price", 0]},
                    "unidentified_average_price": {"$arrayElemAt": ["$unidentified_avg_price.avgUnidentifiedPrice", 0]},
                    "unidentified_average_mid_80_percent_price": {"$arrayElemAt": ["$unidentified_avg_price.average_mid_80_percent_price", 0]}
                }
            }
        ]
    )

    return check_results(result)


def save_lootpool_item(lootpool, environment="prod"):
    """ Save items to the lootpool collection
    """
    collection = get_collection("lootpool", environment)
    if collection is None:
        return jsonify({"message": "Invalid environment. Only prod and dev2 are allowed."}), 400

    print(f"Received lootpool with {len(lootpool.get('items'))} items")

    # Add week and year to the item
    loot_year, loot_week = get_lootpool_week()
    lootpool['week'] = loot_week
    lootpool['year'] = loot_year
    lootpool['timestamp'] = datetime.utcnow()

    # Extract relevant fields to check for duplicates (excluding timestamp)
    pool_check = {
        "region": lootpool.get("region"),
        "week": lootpool.get("week"),
        "year": lootpool.get("year")
    }

    # Check for duplicate items
    duplicate_item = collection.find_one(pool_check)

    if duplicate_item is not None:
        # Get the timestamp of the existing lootpool
        pool_timestamp = duplicate_item['timestamp']
        current_time = datetime.now()
        time_difference = current_time - pool_timestamp

        # Insert conditions
        has_more_items = len(lootpool.get("items")) > len(
            duplicate_item['items'])
        has_more_or_equal_items_and_old = time_difference > timedelta(
            hours=1) and len(lootpool.get("items")) >= len(duplicate_item['items'])
        is_older_week = duplicate_item['week'] < loot_week

        if has_more_items or has_more_or_equal_items_and_old or is_older_week:
            print(
                "New lootpool qualifies for insertion (more items, old data, or older week).")
            collection.delete_one(pool_check)
            collection.insert_one(lootpool)
        else:
            print("Duplicate item found, skipping insertion")
            return {"message": "Duplicate item found, skipping insertion"}, 200
    else:
        print("No duplicate found")
        collection.insert_one(lootpool)

    return {"message": "Item saved successfully"}, 200

def get_lootpool_items(environment="prod"):
    """ Retrieve items from the lootpool collection
    """
    collection = get_collection("lootpool", environment)
    if collection is None:
        return jsonify({"message": "Invalid environment. Only prod and dev2 are allowed."}), 400
    loot_year, loot_week = get_lootpool_week()

    result = collection.aggregate([
        {
            "$match": {
                "week": loot_week,
                "year": loot_year
            }
        },
        {
            "$addFields": {
                "items": {
                    "$map": {
                        "input": "$items",
                        "as": "item",
                        "in": {
                            "$let": {
                                "vars": {
                                    "newRarity": {
                                        "$switch": {
                                            "branches": [
                                                {
                                                    "case": {"$eq": ["$$item.itemType", "AspectItem"]},
                                                    "then": "Aspect"
                                                },
                                                {
                                                    "case": {"$eq": ["$$item.type", "Tome"]},
                                                    "then": "Tome"
                                                }
                                            ],
                                            "default": {
                                                "$ifNull": ["$$item.rarity", "Misc"]
                                            }
                                        }
                                    },
                                    "newType": {
                                        "$cond": {
                                            "if": {"$in": ["$$item.itemType", ["PowderItem", "AmplifierItem"]]},
                                            "then": {
                                                "$reduce": {
                                                    "input": {
                                                        "$slice": [
                                                            {"$split": [
                                                                "$$item.name", " "]},
                                                            0,
                                                            2
                                                        ]
                                                    },
                                                    "initialValue": "",
                                                    "in": {"$concat": ["$$value", "$$this"]}
                                                }
                                            },
                                            "else": "$$item.type"
                                        }
                                    }
                                },
                                "in": {
                                    "$mergeObjects": [
                                        "$$item",
                                        {
                                            "rarity": {"$toLower": "$$newRarity"},
                                            "type": "$$newType"
                                        }
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        },
        {
            "$unwind": "$items"
        },
        {
            "$group": {
                "_id": {
                    "region": "$region",
                    "rarity": "$items.rarity",
                    "shiny": "$items.shiny"
                },
                "itemsList": {
                    "$push": {
                        "itemType": "$items.itemType",
                        "amount": "$items.amount",
                        "name": "$items.name",
                        "type": "$items.type",
                        "rarity": "$items.rarity",
                        "shiny": "$items.shiny"
                    }
                },
                "timestamp": {"$first": "$timestamp"}
            }
        },
        {
            "$addFields": {
                "itemsList": {
                    "$sortArray": {
                        "input": "$itemsList",
                        "sortBy": {"name": 1}
                    }
                }
            }
        },
        {
            "$group": {
                "_id": "$_id.region",
                "week": {"$first": loot_week},
                "year": {"$first": loot_year},
                "timestamp": {"$first": "$timestamp"},
                "itemsByRarity": {
                    "$push": {
                        "rarity": {
                            "$cond": {
                                "if": {"$eq": ["$_id.shiny", True]},
                                "then": "Shiny",
                                "else": {
                                    "$cond": {
                                        "if": {"$eq": ["$_id.rarity", "misc"]},
                                        "then": "Misc",
                                        "else": {
                                            "$let": {
                                                "vars": {
                                                    "rarityLower": "$_id.rarity",
                                                    "rarityLength": {"$strLenCP": "$_id.rarity"}
                                                },
                                                "in": {
                                                    "$concat": [
                                                        {"$toUpper": {"$substr": [
                                                            "$$rarityLower", 0, 1]}},
                                                        {"$substr": ["$$rarityLower", 1, {
                                                            "$subtract": ["$$rarityLength", 1]}]}
                                                    ]
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "shiny": "$_id.shiny",
                        "items": "$itemsList"
                    }
                }
            }
        },
        {
            "$addFields": {
                "itemsByRarity": {
                    "$map": {
                        "input": "$itemsByRarity",
                        "as": "item",
                        "in": {
                            "rarity": "$$item.rarity",
                            "shiny": "$$item.shiny",
                            "items": "$$item.items",
                            "sortKey": {
                                "$switch": {
                                    "branches": [
                                        {"case": {
                                            "$eq": ["$$item.rarity", "Shiny"]}, "then": 0},
                                        {"case": {
                                            "$eq": ["$$item.rarity", "Aspect"]}, "then": 1},
                                        {"case": {
                                            "$eq": ["$$item.rarity", "Mythic"]}, "then": 2},
                                        {"case": {
                                            "$eq": ["$$item.rarity", "Fabled"]}, "then": 3},
                                        {"case": {
                                            "$eq": ["$$item.rarity", "Legendary"]}, "then": 4},
                                        {"case": {
                                            "$eq": ["$$item.rarity", "Rare"]}, "then": 6},
                                        {"case": {
                                            "$eq": ["$$item.rarity", "Set"]}, "then": 7},
                                        {"case": {
                                            "$eq": ["$$item.rarity", "Unique"]}, "then": 8},
                                        {"case": {
                                            "$eq": ["$$item.rarity", "Tome"]}, "then": 9},
                                        {"case": {
                                            "$eq": ["$$item.rarity", "Misc"]}, "then": 10}
                                    ],
                                    "default": 10
                                }
                            }
                        }
                    }
                }
            }
        },
        {
            "$addFields": {
                "itemsByRarity": {
                    "$sortArray": {
                        "input": "$itemsByRarity",
                        "sortBy": {"sortKey": 1}
                    }
                }
            }
        },
        {
            "$project": {
                "_id": 0,
                "region": "$_id",
                "week": 1,
                "year": 1,
                "timestamp": 1,
                "region_items": {
                    "$map": {
                        "input": "$itemsByRarity",
                        "as": "item",
                        "in": {
                            "rarity": "$$item.rarity",
                            "loot_items": {
                                "$map": {
                                    "input": "$$item.items",
                                    "as": "loot_item",
                                    "in": {
                                        "itemType": "$$loot_item.itemType",
                                        "amount": "$$loot_item.amount",
                                        "name": "$$loot_item.name",
                                        "type": "$$loot_item.type",
                                        "rarity": "$$loot_item.rarity",
                                        "shiny": "$$loot_item.shiny"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        {
            "$sort": {"region": 1}
        }
    ])
    
    return check_results(result, custom_message="No lootpool items found for this week")

def get_raidpool_items(environment="prod"):
    """ Retrieve items from the raidpool collection
    """
    collection = get_collection("raidpool", environment)
    if collection is None:
        return jsonify({"message": "Invalid environment. Only prod and dev2 are allowed."}), 400
    loot_year, loot_week = get_lootpool_week()

    result = collection.aggregate([
        # Match documents for the given week and year
        {
            "$match": {
                "week": loot_week,
                "year": loot_year
            }
        },
        # Unwind the items array to process each item individually
        {
            "$unwind": "$items"
        },
        # Normalize the rarity field and handle null values
        {
            "$addFields": {
                "items": {
                    "$mergeObjects": [
                        "$items",
                        {
                            "rarity": {
                                "$toLower": {
                                    "$ifNull": ["$items.rarity", "Common"]
                                }
                            }
                        }
                    ]
                }
            }
        },
        # Group items by region, normalized rarity, and shiny status
        {
            "$group": {
                "_id": {
                    "region": "$region",
                    "rarity": "$items.rarity",
                    "shiny": "$items.shiny"
                },
                "itemsList": {
                    "$push": {
                        "itemType": "$items.itemType",
                        "amount": "$items.amount",
                        "name": "$items.name",
                        "type": "$items.type",
                        "rarity": "$items.rarity",
                        "shiny": "$items.shiny"
                    }
                },
                "timestamp": {"$first": "$timestamp"}
            }
        },
        # Sort itemsList by name within each group
        {
            "$addFields": {
                "itemsList": {
                    "$sortArray": {
                        "input": "$itemsList",
                        "sortBy": {"name": 1}
                    }
                }
            }
        },
        # Group by region and prepare itemsByRarity
        {
            "$group": {
                "_id": "$_id.region",
                "week": {"$first": loot_week},
                "year": {"$first": loot_year},
                "timestamp": { "$first": "$timestamp" },
                "itemsByRarity": {
                    "$push": {
                        "rarity": {
                            "$cond": {
                                "if": {"$eq": ["$_id.shiny", True]},
                                "then": "Shiny",
                                "else": {
                                    "$cond": {
                                        "if": {"$eq": ["$_id.rarity", "misc"]},
                                        "then": "Misc",
                                        "else": {
                                            "$concat": [
                                                {"$toUpper": {"$substr": ["$_id.rarity", 0, 1]}},
                                                {"$substr": ["$_id.rarity", 1, {"$subtract": [{"$strLenCP": "$_id.rarity"}, 1]}]}
                                            ]
                                        }
                                    }
                                }
                            }
                        },
                        "shiny": "$_id.shiny",
                        "items": "$itemsList"
                    }
                }
            }
        },
        # Map over itemsByRarity to assign sortKey
        {
            "$addFields": {
                "itemsByRarity": {
                    "$map": {
                        "input": "$itemsByRarity",
                        "as": "item",
                        "in": {
                            "rarity": "$$item.rarity",
                            "shiny": "$$item.shiny",
                            "items": "$$item.items",
                            "sortKey": {
                                "$switch": {
                                    "branches": [
                                        {"case": {"$eq": ["$$item.rarity", "Shiny"]}, "then": 0},
                                        {"case": {"$eq": ["$$item.rarity", "Aspect"]}, "then": 1},
                                        {"case": {"$eq": ["$$item.rarity", "Mythic"]}, "then": 2},
                                        {"case": {"$eq": ["$$item.rarity", "Fabled"]}, "then": 3},
                                        {"case": {"$eq": ["$$item.rarity", "Legendary"]}, "then": 4},
                                        {"case": {"$eq": ["$$item.rarity", "Rare"]}, "then": 6},
                                        {"case": {"$eq": ["$$item.rarity", "Set"]}, "then": 7},
                                        {"case": {"$eq": ["$$item.rarity", "Unique"]}, "then": 8},
                                        {"case": {"$eq": ["$$item.rarity", "Tome"]}, "then": 9},
                                        {"case": {"$eq": ["$$item.rarity", "Common"]}, "then": 10}
                                    ],
                                    "default": 10
                                }
                            }
                        }
                    }
                }
            }
        },
        # Sort itemsByRarity based on sortKey
        {
            "$addFields": {
                "itemsByRarity": {
                    "$sortArray": {
                        "input": "$itemsByRarity",
                        "sortBy": {"sortKey": 1}
                    }
                }
            }
        },
        # Project the final output
        {
            "$project": {
                "_id": 0,
                "region": "$_id",
                "week": 1,
                "year": 1,
                "timestamp": 1,
                "region_items": {
                    "$map": {
                        "input": "$itemsByRarity",
                        "as": "item",
                        "in": {
                            "rarity": "$$item.rarity",
                            "loot_items": "$$item.items"
                        }
                    }
                }
            }
        },
        # Sort the final results by region
        {
            "$sort": {"region": 1}
        }
    ])


    return check_results(result, custom_message="No lootpool items found for this week")


def save_raidpool_item(raidpool, environment="prod"):
    """ Save items to the raidpool collection
    """
    collection = get_collection("raidpool", environment)
    if collection is None:
        return jsonify({"message": "Invalid environment. Only prod and dev2 are allowed."}), 400

    print(f"Received raidpool with {len(raidpool.get('items'))} items")

    # Add week and year to the item
    loot_year, loot_week = get_lootpool_week()
    raidpool['week'] = loot_week
    raidpool['year'] = loot_year
    raidpool['timestamp'] = datetime.utcnow()

    # Extract relevant fields to check for duplicates (excluding timestamp)
    pool_check = {
        "region": raidpool.get("region"),
        "week": raidpool.get("week"),
        "year": raidpool.get("year")
    }

    # Check for duplicate items
    duplicate_item = collection.find_one(pool_check)

    if duplicate_item is not None:
        # Get the timestamp of the existing lootpool
        pool_timestamp = duplicate_item['timestamp']
        current_time = datetime.now()
        time_difference = current_time - pool_timestamp

        # Insert conditions
        has_more_items = len(raidpool.get("items")) > len(
            duplicate_item['items'])
        has_more_or_equal_items_and_old = time_difference > timedelta(
            hours=1) and len(raidpool.get("items")) >= len(duplicate_item['items'])
        is_older_week = duplicate_item['week'] < loot_week

        if has_more_items or has_more_or_equal_items_and_old or is_older_week:
            print(
                "New raidpool qualifies for insertion (more items, old data, or older week).")
            collection.delete_one(pool_check)
            collection.insert_one(raidpool)
        else:
            print("Duplicate item found, skipping insertion")
            return {"message": "Duplicate item found, skipping insertion"}, 200
    else:
        print("No duplicate found")
        collection.insert_one(raidpool)

    return {"message": "Item saved successfully"}, 200


def check_results(result, custom_message="No items found"):
    """ Check if the result is empty and return a custom message
    """
    result = list(result)
    if result == [] or result == [{}]:
        return jsonify({"message": custom_message}), 404
    return jsonify(result), 200


def get_collection(collection, environment="prod"):
    """ Get the collection based on the type and environment
    """
    if collection == "trademarket":
        if environment == "prod":
            return db[PROD_MARKET_DB]
        elif environment == "dev" or environment == "dev2":
            return db[DEV_MARKET_DB]
    elif collection == "lootpool":
        if environment == "prod":
            return db[PROD_LOOT_DB]
        elif environment == "dev" or environment == "dev2":
            return db[DEV_LOOT_DB]
    elif collection == "raidpool":
        if environment == "prod":
            return db[PROD_RAID_DB]
        elif environment == "dev" or environment == "dev2":
            return db[DEV_RAID_DB]
