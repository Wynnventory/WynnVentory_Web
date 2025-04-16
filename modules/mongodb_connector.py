from datetime import datetime, timedelta
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from flask import jsonify
import logging


from modules.utils import get_lootpool_week, get_lootpool_week_for_timestamp, get_raidpool_week

uri = "mongodb+srv://Test1234:Test1234@wynnventory.9axarep.mongodb.net/?retryWrites=true&w=majority&appName=wynnventory"
PROD_MARKET_DB = "trademarket_items_PROD"
DEV_MARKET_DB = "trademarket_items_DEV"
PROD_LOOT_DB = "lootpool_items_PROD"
DEV_LOOT_DB = "lootpool_items_DEV"
PROD_RAID_DB = "raidpool_items_PROD"
DEV_RAID_DB = "raidpool_items_DEV"
PROD_MARKET_ARCH_DB = "tm_items_ARCH_PROD"
DEV_MARKET_ARCH_DB = "tm_items_ARCH_DEV"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
        "rarity": item.get("rarity"),
        "unidentified": item.get("unidentified"),
        "shiny_stat": item.get("shiny_stat"),
        "amount": item.get("amount"),
        "listing_price": item.get("listing_price"),
        "hash_code": item.get("hash_code"),
        "item_type": item.get("item_type"),
        "type": item.get("type")
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


def get_trade_market_item_price(item_name, shiny: bool = False, environment="prod"):
    """ Retrieve price of item from the trademarket collection
    """
    collection = get_collection("trademarket", environment)

    if shiny:
        shinyStat = "$ne"
    else:
        shinyStat = "$eq"

    result = collection.aggregate(
        [
            {
                "$match": {
                    "name": item_name,
                    "shiny_stat": {shinyStat: None}
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

    # print(f"Received lootpool with {len(lootpool.get('items'))} items")

    # Add week and year to the item
    loot_year, loot_week = get_lootpool_week_for_timestamp(lootpool.get('collectionTime'))
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
    # print(f"Duplicate item: {duplicate_item}")

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
        is_older_week = duplicate_item['week'] < loot_week or duplicate_item['year'] < loot_year

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
        # Match documents for the given week and year
        {
            "$match": {
                "week": loot_week,
                "year": loot_year
            }
        },
        # Map over items to assign 'group' and 'newType' fields
        {
            "$addFields": {
                "items": {
                    "$map": {
                        "input": "$items",
                        "as": "item",
                        "in": {
                            "$let": {
                                "vars": {
                                    # Determine the group for each item
                                    "group": {
                                        "$switch": {
                                            "branches": [
                                                # If itemType is 'AspectItem', group is 'Aspect'
                                                {
                                                    "case": { "$eq": ["$$item.itemType", "AspectItem"] },
                                                    "then": "Aspect"
                                                },
                                                # If type contains 'TOME' (case-insensitive), group is 'Tomes'
                                                {
                                                    "case": {
                                                        "$regexMatch": {
                                                            "input": "$$item.type",
                                                            "regex": "TOME",
                                                            "options": "i"
                                                        }
                                                    },
                                                    "then": "Tomes"
                                                }
                                            ],
                                            # Default group is the item's rarity (properly formatted), or 'Misc'
                                            "default": {
                                                "$cond": {
                                                    "if": { "$ne": ["$$item.rarity", None] },
                                                    "then": {
                                                        "$concat": [
                                                            { "$toUpper": { "$substr": ["$$item.rarity", 0, 1] } },
                                                            {
                                                                "$substr": [
                                                                    "$$item.rarity",
                                                                    1,
                                                                    { "$subtract": [{ "$strLenCP": "$$item.rarity" }, 1] }
                                                                ]
                                                            }
                                                        ]
                                                    },
                                                    "else": "Misc"
                                                }
                                            }
                                        }
                                    },
                                    # Determine the new type for specific itemTypes
                                    "newType": {
                                        "$cond": {
                                            "if": { "$in": ["$$item.itemType", ["PowderItem", "AmplifierItem"]] },
                                            "then": {
                                                "$reduce": {
                                                    "input": {
                                                        "$slice": [
                                                            { "$split": ["$$item.name", " "] },
                                                            0,
                                                            2
                                                        ]
                                                    },
                                                    "initialValue": "",
                                                    "in": { "$concat": ["$$value", "$$this"] }
                                                }
                                            },
                                            "else": "$$item.type"
                                        }
                                    }
                                },
                                "in": {
                                    # Merge the new fields back into the item
                                    "$mergeObjects": [
                                        "$$item",
                                        {
                                            "group": "$$group",
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
        # Unwind the items array to process each item individually
        {
            "$unwind": "$items"
        },
        # Group items by region, group, and shiny status
        {
            "$group": {
                "_id": {
                    "region": "$region",
                    "group": { "$toLower": "$items.group" },
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
                "timestamp": { "$first": "$timestamp" }
            }
        },
        # Sort itemsList by name within each group
        {
            "$addFields": {
                "itemsList": {
                    "$sortArray": {
                        "input": "$itemsList",
                        "sortBy": { "name": 1 }
                    }
                }
            }
        },
        # Group by region to assemble the final structure with itemsByGroup
        {
            "$group": {
                "_id": "$_id.region",
                "week": { "$first": loot_week },
                "year": { "$first": loot_year },
                "timestamp": { "$first": "$timestamp" },
                "itemsByGroup": {
                    "$push": {
                        "group": {
                            "$cond": {
                                "if": { "$eq": ["$_id.shiny", True] },
                                "then": "Shiny",
                                "else": {
                                    "$let": {
                                        "vars": {
                                            "groupLower": "$_id.group",
                                            "groupLength": { "$strLenCP": "$_id.group" }
                                        },
                                        "in": {
                                            "$concat": [
                                                { "$toUpper": { "$substr": ["$$groupLower", 0, 1] } },
                                                {
                                                    "$substr": [
                                                        "$$groupLower",
                                                        1,
                                                        { "$subtract": ["$$groupLength", 1] }
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
        # Assign sortKey based on group for ordering
        {
            "$addFields": {
                "itemsByGroup": {
                    "$map": {
                        "input": "$itemsByGroup",
                        "as": "item",
                        "in": {
                            "group": "$$item.group",
                            "shiny": "$$item.shiny",
                            "items": "$$item.items",
                            "sortKey": {
                                "$switch": {
                                    "branches": [
                                        { "case": { "$eq": ["$$item.group", "Shiny"] }, "then": 0 },
                                        { "case": { "$eq": ["$$item.group", "Aspect"] }, "then": 1 },
                                        { "case": { "$eq": ["$$item.group", "Mythic"] }, "then": 2 },
                                        { "case": { "$eq": ["$$item.group", "Fabled"] }, "then": 3 },
                                        { "case": { "$eq": ["$$item.group", "Legendary"] }, "then": 4 },
                                        { "case": { "$eq": ["$$item.group", "Rare"] }, "then": 5 },
                                        { "case": { "$eq": ["$$item.group", "Set"] }, "then": 6 },
                                        { "case": { "$eq": ["$$item.group", "Unique"] }, "then": 7 },
                                        { "case": { "$eq": ["$$item.group", "Tomes"] }, "then": 8 },
                                        { "case": { "$eq": ["$$item.group", "Common"] }, "then": 9 },
                                        { "case": { "$eq": ["$$item.group", "Misc"] }, "then": 10 }
                                    ],
                                    "default": 11
                                }
                            }
                        }
                    }
                }
            }
        },
        # Sort the itemsByGroup array based on sortKey
        {
            "$addFields": {
                "itemsByGroup": {
                    "$sortArray": {
                        "input": "$itemsByGroup",
                        "sortBy": { "sortKey": 1 }
                    }
                }
            }
        },
        # Project the final output, including the original rarity of items
        {
            "$project": {
                "_id": 0,
                "region": "$_id",
                "week": 1,
                "year": 1,
                "timestamp": 1,
                "region_items": {
                    "$map": {
                        "input": "$itemsByGroup",
                        "as": "item",
                        "in": {
                            "group": "$$item.group",
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
        # Sort the final results by region
        {
            "$sort": { "region": 1 }
        }
    ])

    return check_results(result, custom_message="No lootpool items found for this week")

def get_lootpool_items_raw(environment="prod"):
    """ Retrieve items from the lootpool collection
    """
    collection = get_collection("lootpool", environment)
    if collection is None:
        return jsonify({"message": "Invalid environment. Only prod and dev2 are allowed."}), 400
    loot_year, loot_week = get_lootpool_week()

    result = collection.find(
        filter={'week': loot_week, 'year': loot_year},
        projection={'_id': 0}
    )

    return check_results(result, custom_message="No lootpool items found for this week")

def get_raidpool_items_raw(environment="prod"):
    """ Retrieve items from the raidpool collection
    """
    collection = get_collection("raidpool", environment)
    if collection is None:
        return jsonify({"message": "Invalid environment. Only prod and dev2 are allowed."}), 400
    loot_year, loot_week = get_raidpool_week()

    result = collection.find(
        filter={'week': loot_week, 'year': loot_year},
        projection={'_id': 0}
    )

    return check_results(result, custom_message="No lootpool items found for this week")

def get_raidpool_items(environment="prod"):
    """ Retrieve items from the raidpool collection
    """
    collection = get_collection("raidpool", environment)
    if collection is None:
        return jsonify({"message": "Invalid environment. Only prod and dev2 are allowed."}), 400
    loot_year, loot_week = get_raidpool_week()

    result = collection.aggregate([
        # Match documents for the given week and year
        {
            "$match": {
                "week": loot_week,
                "year": loot_year
            }
        },
        # Add 'group', 'rarityFormatted', and 'rarityLower' fields to each item
        {
            "$addFields": {
                "items": {
                    "$map": {
                        "input": "$items",
                        "as": "item",
                        "in": {
                            "$mergeObjects": [
                                "$$item",
                                {
                                    # Assign 'group' based on itemType and type
                                    "group": {
                                        "$switch": {
                                            "branches": [
                                                {
                                                    "case": { "$eq": ["$$item.itemType", "AspectItem"] },
                                                    "then": "Aspects"
                                                },
                                                {
                                                    "case": { "$eq": ["$$item.itemType", "GearItem"] },
                                                    "then": "Gear"
                                                },
                                                {
                                                    "case": {
                                                        "$regexMatch": {
                                                            "input": "$$item.type",
                                                            "regex": "TOME",
                                                            "options": "i"
                                                        }
                                                    },
                                                    "then": "Tomes"
                                                },
                                                {
                                                    "case": {
                                                        "$in": ["$$item.itemType", ["PowderItem", "EmeraldItem", "AmplifierItem"]]
                                                    },
                                                    "then": "Misc"
                                                }
                                            ],
                                            "default": "Other"
                                        }
                                    },
                                    # Format 'rarity' with only the first character uppercase
                                    "rarityFormatted": {
                                        "$cond": {
                                            "if": { "$ne": ["$$item.rarity", None] },
                                            "then": {
                                                "$concat": [
                                                    {
                                                        "$toUpper": {
                                                            "$substr": ["$$item.rarity", 0, 1]
                                                        }
                                                    },
                                                    {
                                                        "$toLower": {
                                                            "$substr": [
                                                                "$$item.rarity",
                                                                1,
                                                                { "$strLenCP": "$$item.rarity" }
                                                            ]
                                                        }
                                                    }
                                                ]
                                            },
                                            "else": ""
                                        }
                                    },
                                    # Store 'rarity' in lowercase for consistent comparisons
                                    "rarityLower": {
                                        "$toLower": {
                                            "$ifNull": ["$$item.rarity", ""]
                                        }
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        },
        # Unwind the items array to process each item individually
        {
            "$unwind": "$items"
        },
        # Group items by region and the new 'group' field
        {
            "$group": {
                "_id": {
                    "region": "$region",
                    "group": "$items.group"
                },
                "itemsList": {
                    "$push": "$items"
                },
                "timestamp": { "$first": "$timestamp" }
            }
        },
        # Assign 'raritySortKey' to items in 'itemsList' based on 'rarityLower'
        {
            "$addFields": {
                "itemsList": {
                    "$map": {
                        "input": "$itemsList",
                        "as": "item",
                        "in": {
                            "$mergeObjects": [
                                "$$item",
                                {
                                    "raritySortKey": {
                                        "$switch": {
                                            "branches": [
                                                { "case": { "$eq": ["$$item.rarityLower", "mythic"] }, "then": 1 },
                                                { "case": { "$eq": ["$$item.rarityLower", "fabled"] }, "then": 2 },
                                                { "case": { "$eq": ["$$item.rarityLower", "legendary"] }, "then": 3 },
                                                { "case": { "$eq": ["$$item.rarityLower", "rare"] }, "then": 4 },
                                                { "case": { "$eq": ["$$item.rarityLower", "unique"] }, "then": 5 },
                                                { "case": { "$eq": ["$$item.rarityLower", "common"] }, "then": 6 },
                                                { "case": { "$eq": ["$$item.rarityLower", "set"] }, "then": 7 }
                                            ],
                                            "default": 8  # For rarities not specified
                                        }
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        },
        # Group by region to assemble the final structure
        {
            "$group": {
                "_id": "$_id.region",
                "week": { "$first": loot_week },
                "year": { "$first": loot_year },
                "timestamp": { "$first": "$timestamp" },
                "itemsByGroup": {
                    "$push": {
                        "group": "$_id.group",
                        "items": "$itemsList"
                    }
                }
            }
        },
        # Assign 'groupSortKey' to each group for ordering
        {
            "$addFields": {
                "itemsByGroup": {
                    "$map": {
                        "input": "$itemsByGroup",
                        "as": "item",
                        "in": {
                            "$mergeObjects": [
                                "$$item",
                                {
                                    "groupSortKey": {
                                        "$switch": {
                                            "branches": [
                                                { "case": { "$eq": ["$$item.group", "Aspects"] }, "then": 1 },
                                                { "case": { "$eq": ["$$item.group", "Tomes"] }, "then": 2 },
                                                { "case": { "$eq": ["$$item.group", "Gear"] }, "then": 3 },
                                                { "case": { "$eq": ["$$item.group", "Misc"] }, "then": 4 }
                                            ],
                                            "default": 5  # 'Other' or any unspecified group
                                        }
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        },
        # Sort the 'itemsByGroup' array based on 'groupSortKey'
        {
            "$addFields": {
                "itemsByGroup": {
                    "$sortArray": {
                        "input": "$itemsByGroup",
                        "sortBy": { "groupSortKey": 1 }
                    }
                }
            }
        },
        # Sort 'items' within each group differently based on 'group'
        {
            "$addFields": {
                "itemsByGroup": {
                    "$map": {
                        "input": "$itemsByGroup",
                        "as": "groupItem",
                        "in": {
                            "$mergeObjects": [
                                "$$groupItem",
                                {
                                    "items": {
                                        "$cond": [
                                            { "$eq": ["$$groupItem.group", "Aspects"] },
                                            {
                                                "$sortArray": {
                                                    "input": "$$groupItem.items",
                                                    "sortBy": {
                                                        "raritySortKey": 1,
                                                        "type": 1,
                                                        "name": 1
                                                    }
                                                }
                                            },
                                            {
                                                "$sortArray": {
                                                    "input": "$$groupItem.items",
                                                    "sortBy": {
                                                        "raritySortKey": 1,
                                                        "name": 1
                                                    }
                                                }
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        },
        # Project the final output, using 'rarityFormatted' for display
        {
            "$project": {
                "_id": 0,
                "region": "$_id",
                "week": 1,
                "year": 1,
                "timestamp": 1,
                "group_items": {
                    "$map": {
                        "input": "$itemsByGroup",
                        "as": "groupItem",
                        "in": {
                            "group": "$$groupItem.group",
                            "loot_items": {
                                "$map": {
                                    "input": "$$groupItem.items",
                                    "as": "item",
                                    "in": {
                                        "name": "$$item.name",
                                        "type": "$$item.type",
                                        "rarity": "$$item.rarityFormatted",
                                        "itemType": "$$item.itemType",
                                        "amount": "$$item.amount",
                                        "shiny": "$$item.shiny"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        # Sort the final results by region
        {
            "$sort": { "region": 1 }
        }
    ])

    return check_results(result, custom_message="No lootpool items found for this week")


def save_raidpool_item(raidpool, environment="prod"):
    """ Save items to the raidpool collection
    """
    collection = get_collection("raidpool", environment)
    if collection is None:
        return jsonify({"message": "Invalid environment. Only prod and dev2 are allowed."}), 400

    # print(f"Received raidpool with {len(raidpool.get('items'))} items")

    # Add week and year to the item
    loot_year, loot_week = get_raidpool_week()
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
        is_older_week = duplicate_item['week'] < loot_week or duplicate_item['year'] < loot_year

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

def get_price_history(item_name, environment="prod", days=None):
    """ Retrieve the price history of an item from the trademarket collection """
    collection = get_collection("trademarket_ARCH", environment)

    # Base filter for item name
    query_filter = { 'name': item_name }

    # If a timeframe is provided, filter by date (assumes 'date' field is a datetime)
    if days:
        try:
            days_int = int(days) + 8
            start_date = datetime.utcnow() - timedelta(days=days_int)
            query_filter['date'] = {'$gte': start_date}
        except ValueError:
            # If days is not an integer, ignore the filter or handle error as needed
            pass

    sort = list({ 'date': 1 }.items())

    result = collection.find(
        filter=query_filter,
        sort=sort,
        projection={'_id': 0}
    )

    return check_results(result, custom_message="No items found with that name")

def get_latest_price_history(item_name, environment="prod"):
    """Retrieve the averaged stats of an item from the trademarket collection using the 4 most recent documents."""
    collection = get_collection("trademarket_ARCH", environment)

    # Filter by the item name
    query_filter = { 'name': item_name }

    # Sort descending by date so that the most recent documents are first
    sort = [('date', -1)]
    # Retrieve only the 4 most recent documents
    cursor = collection.find(
        filter=query_filter,
        sort=sort,
        projection={'_id': 0}  # Exclude _id from results
    ).limit(7)

    docs = list(cursor)
    if not docs:
        return check_results(cursor, custom_message="No items found with that name")

    # Define the fields to calculate averages for.
    # (Excludes 'name' and 'date' since those are not numeric stats.)
    stat_fields = [
        "lowest_price",
        "highest_price",
        "average_price",
        "total_count",
        "average_mid_80_percent_price",
        "unidentified_average_price",
        "unidentified_average_mid_80_percent_price",
        "unidentified_count"
    ]

    averages = {}
    for field in stat_fields:
        # Gather all non-null values for this field across the documents
        values = [doc[field] for doc in docs if doc.get(field) is not None]
        # Calculate the average if there are any valid values
        if values:
            averages[field] = sum(values) / len(values)
        else:
            averages[field] = None

    averages["name"] = item_name

    # Optionally include the count of documents used in the calculation
    averages['document_count'] = len(docs)

    return averages

def get_all_items_ranking(environment="prod"):
    """
    Retrieve ranking data for all items from the archive collection.
    """
    collection = get_collection("trademarket_ARCH", environment)

    # Example aggregation pipeline:
    # 1) Group documents by item name, computing relevant stats
    # 2) Sort by average_price descending
    pipeline = [
        {
            "$group": {
                "_id": "$name",
                "lowest_price": {"$min": "$lowest_price"},
                "highest_price": {"$max": "$highest_price"},
                "average_price": {"$avg": "$average_price"},
                "average_total_count": {"$avg": "$total_count"},
                "average_unidentified_count": {"$avg": "$unidentified_count"},
                "average_mid_80_percent_price": {"$avg": "$average_mid_80_percent_price"},
                "unidentified_average_mid_80_percent_price": {"$avg": "$unidentified_average_mid_80_percent_price"},
                "dates": {"$push": "$date"}
            }
        },
        # Exclude documents where average_mid_80_percent_price < 1024
        {
            "$match": {
                "average_mid_80_percent_price": {"$gte": 20480},
                "average_total_count": {"$gte": 2}
            }
        },
        {
            "$sort": {"average_price": -1}
        }
    ]

    results = collection.aggregate(pipeline)
    return check_results(results, custom_message="No items found in archive.")


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
    elif collection == "trademarket_ARCH":
        if environment == "prod":
            return db[PROD_MARKET_ARCH_DB]
        elif environment == "dev" or environment == "dev2":
            return db[DEV_MARKET_ARCH_DB]

    return None
