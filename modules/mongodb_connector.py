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
                                                {"$ceil": {"$multiply": [{"$size": "$prices"}, 0.1]}},
                                                {"$floor": {"$multiply": [{"$size": "$prices"}, 0.8]}}
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
                                                {"$ceil": {"$multiply": [{"$size": "$prices"}, 0.1]}},
                                                {"$floor": {"$multiply": [{"$size": "$prices"}, 0.8]}}
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
        pool_timestamp = duplicate_item['timestamp'] # Get the timestamp of the existing lootpool
        current_time = datetime.now()
        time_difference = current_time - pool_timestamp
        
        if time_difference > timedelta(hours=1) or len(lootpool.get("items")) > len(duplicate_item['items']):
            if time_difference > timedelta(hours=1):
                print("The timestamp is more than 1 hour old.")
            elif len(lootpool.get("items")) > len(duplicate_item['items']):
                print("The new lootpool has more items than the existing one.")
            collection.delete_one(pool_check)
            collection.insert_one(lootpool)
        else:
            return {"message": "Duplicate item found, skipping insertion"}, 200
    else: # No duplicate found
        collection.insert_one(lootpool)
        
    return {"message": "Item saved successfully"}, 200


def get_lootpool_items(environment="prod"):
    """ Retrieve items from the trademarket collection by name
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
        }
        }
    },
    {
        "$group": {
        "_id": "$_id.region", 
        "week": {
            "$first": loot_week
        }, 
        "year": {
            "$first": loot_year
        }, 
        "itemsByRarity": {
            "$push": {
            "rarity": {
                "$cond": {
                "if": {
                    "$eq": [
                    "$_id.shiny", True
                    ]
                }, 
                "then": "Shiny", 
                "else": {
                    "$cond": {
                    "if": {
                        "$eq": ["$_id.rarity", None]
                    }, 
                    "then": "Misc", 
                    "else": {
                        "$concat": [
                        {
                            "$toUpper": {
                            "$substr": [
                                "$_id.rarity", 0, 1
                            ]
                            }
                        }, 
                        {
                            "$substr": [
                            "$_id.rarity", 1, {
                                "$strLenCP": "$_id.rarity"
                            }
                            ]
                        }
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
                    {
                        "case": {
                        "$eq": [
                            "$$item.rarity", "Shiny"
                        ]
                        }, 
                        "then": 0
                    }, 
                    {
                        "case": {
                        "$eq": [
                            "$$item.rarity", "Mythic"
                        ]
                        }, 
                        "then": 1
                    }, 
                    {
                        "case": {
                        "$eq": [
                            "$$item.rarity", "Fabled"
                        ]
                        }, 
                        "then": 2
                    }, 
                    {
                        "case": {
                        "$eq": [
                            "$$item.rarity", "Legendary"
                        ]
                        }, 
                        "then": 3
                    }, 
                    {
                        "case": {
                        "$eq": [
                            "$$item.rarity", "Rare"
                        ]
                        }, 
                        "then": 4
                    }, 
                    {
                        "case": {
                        "$eq": [
                            "$$item.rarity", "Unique"
                        ]
                        }, 
                        "then": 5
                    }, 
                    {
                        "case": {
                        "$eq": [
                            "$$item.rarity", "Misc"
                        ]
                        }, 
                        "then": 6
                    }
                    ], 
                    "default": 7
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
            "sortBy": {
                "sortKey": 1
            }
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
        "$sort": {
        "region": 1
        }
    }
    ]
    )
    return check_results(result, custom_message="No lootpool items found for this week")


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
