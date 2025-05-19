from typing import List, Dict, Any, Optional, Union

from modules.db import get_collection
from modules.models.collection_types import Collection
from modules.repositories.base_pool_repo import BasePoolRepo
from modules.utils.time_validation import get_lootpool_week

# Initialize the base repository and aggregator with the LOOT collection type
_repo = BasePoolRepo(Collection.LOOT)

def save(pool: dict) -> None:
    """
    Insert or update a lootpool document for the given region/week/year,
    applying duplicate checks and timestamp logic.
    """
    _repo.save(pool)


def fetch_lootpools(year: Optional[int] = None, week: Optional[int] = None) -> Union[Dict, List[Dict]]:
    """
    If both year and week are passed, returns a single dict (or {} if none found).
    If neither is passed, returns a List of every year/week doc.
    """

    pipeline = _build_lootpool_pipeline(year, week)
    cursor = get_collection(Collection.LOOT).aggregate(pipeline)

    # single‐object case
    if year is not None and week is not None:
        try:
            return cursor.next()
        except StopIteration:
            return {}

    # “all” case
    return list(cursor)


# OLD GROUPED FORMAT
def fetch_lootpool() -> List[dict]:
    """
    Retrieve the processed lootpool items for the current week/year,
    grouped and sorted by region, group, and shiny status.
    """

    year, week = get_lootpool_week()
    pipeline = [
        # Match documents for the given week and year
        {
            "$match": {
                "week": week,
                "year": year
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
                "week": { "$first": week },
                "year": { "$first": year },
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
    ]

    cursor = get_collection(Collection.LOOT).aggregate(pipeline)
    return list(cursor)


def _build_lootpool_pipeline(year: Optional[int] = None,
                             week: Optional[int] = None) -> List[Dict]:
    pipeline: List[Dict] = []

    # 1) optionally match this week/year
    if year is not None and week is not None:
        pipeline.append({"$match": {"year": year, "week": week}})
    elif (year is None) ^ (week is None):
        # one without the other is invalid
        raise ValueError("Both year and week must be provided, or neither.")

    # 2) unwind the items array
    pipeline.append({"$unwind": "$items"})

    # 3) tag each item with category = "Shiny" if shiny, else by rarity; copy type→subtype
    pipeline.append({
        "$set": {
            "items.subtype": "$items.type",
            "items.category": {
                "$cond": ["$items.shiny", "Shiny", "$items.rarity"]
            }
        }
    })

    # 4) group by region+category, building itemName→itemDetails KV pairs
    pipeline.append({
        "$group": {
            "_id": {
                "year":     "$year",
                "week":     "$week",
                "region":   "$region",
                "timestamp":"$timestamp",
                "category": "$items.category"
            },
            "itemsKV": {"$push": {
                "k": "$items.name",
                "v": {
                    "amount":   "$items.amount",
                    "rarity":   "$items.rarity",
                    "shiny":    "$items.shiny",
                    "itemType": "$items.itemType",
                    "subtype":  "$items.subtype",
                    "shinyStat":"$items.shinyStat"
                }
            }}
        }
    })

    # 5) assemble each region’s categories into categoryName→(itemObject)
    pipeline.append({
        "$group": {
            "_id": {
                "year":     "$_id.year",
                "week":     "$_id.week",
                "region":   "$_id.region",
                "timestamp":"$_id.timestamp"
            },
            "categories": {"$push": {
                "k": "$_id.category",
                "v": {"$arrayToObject": "$itemsKV"}
            }}
        }
    })

    # 6) project region‐level docs flat so we can group them
    pipeline.append({
        "$project": {
            "year":      "$_id.year",
            "week":      "$_id.week",
            "region":    "$_id.region",
            "timestamp": "$_id.timestamp",
            "categories": 1
        }
    })

    # 7) gather all regions under each year/week, merging ts+categories
    pipeline.append({
        "$group": {
            "_id": {"year": "$year", "week": "$week"},
            "regions": {"$push": {
                "k": "$region",
                "v": {"$mergeObjects": [
                    {"timestamp": "$timestamp"},
                    {"$arrayToObject": "$categories"}
                ]}
            }}
        }
    })

    # 8) replace with { year, week, <region>:{…}, … }
    pipeline.append({
        "$replaceWith": {
            "$mergeObjects": [
                {"year": "$_id.year", "week": "$_id.week"},
                {"$arrayToObject": "$regions"}
            ]
        }
    })

    return pipeline

