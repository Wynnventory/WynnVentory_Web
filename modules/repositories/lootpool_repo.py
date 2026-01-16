from typing import List, Dict, Any, Optional, Union

from modules.db import get_collection
from modules.models.collection_types import Collection
from modules.repositories.base_pool_repo import BasePoolRepo, build_pool_pipeline
from modules.utils.time_validation import get_lootpool_week

# Initialize the base repository and aggregator with the LOOT collection type
_repo = BasePoolRepo(Collection.LOOT)


def save(pool: dict) -> None:
    """
    Insert or update a lootpool document for the given region/week/year,
    applying duplicate checks and timestamp logic.
    """
    _repo.save(pool)


def fetch_lootpools(
        year: Optional[int] = None,
        week: Optional[int] = None,
        page: Optional[int] = 1,
        page_size: Optional[int] = 100,
        skip: Optional[int] = 0
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    If both year and week are passed, returns a single dict (or {} if none found).
    If neither is passed, returns a paginated Dict:
      {
        'page': int,
        'page_size': int,
        'count': int,
        'pools': List[Dict]
      }
    """
    coll = get_collection(Collection.LOOT)
    pipeline = build_pool_pipeline(year, week)

    # 1) Single‐object case
    if year is not None and week is not None:
        cursor = coll.aggregate(pipeline)
        try:
            return cursor.next()
        except StopIteration:
            return {}

    paged_pipeline = pipeline + [
        {"$skip": skip},
        {"$limit": page_size}
    ]

    # 2) Paginated “all” case
    results = list(coll.aggregate(paged_pipeline))

    return {
        "page": page,
        "page_size": page_size,
        "count": len(results),
        "pools": results
    }


def fetch_lootpool() -> List[dict]:
    """
    Retrieve the processed lootpool items for the current week/year,
    grouped and sorted by region, group, and shiny status.

    Change: items that don't have a shinyStat are NOT treated as shiny for grouping.
            (effectiveShiny = shiny == True AND shinyStat exists/not-null)
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

        # Map over items to assign 'group' and 'type' fields
        # + compute effectiveShiny and override items.shiny with it for downstream grouping
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
                                                    "case": {"$eq": ["$$item.itemType", "AspectItem"]},
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
                                                    "if": {"$ne": ["$$item.rarity", None]},
                                                    "then": {
                                                        "$concat": [
                                                            {"$toUpper": {"$substr": ["$$item.rarity", 0, 1]}},
                                                            {
                                                                "$substr": [
                                                                    "$$item.rarity",
                                                                    1,
                                                                    {"$subtract": [{"$strLenCP": "$$item.rarity"}, 1]}
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
                                            "if": {"$in": ["$$item.itemType", ["PowderItem", "AmplifierItem"]]},
                                            "then": {
                                                "$reduce": {
                                                    "input": {
                                                        "$slice": [
                                                            {"$split": ["$$item.name", " "]},
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
                                    },

                                    # NEW: treat as shiny only if shiny==true AND shinyStat exists/not-null
                                    "effectiveShiny": {
                                        "$and": [
                                            {"$eq": ["$$item.shiny", True]},
                                            {"$ne": [{"$ifNull": ["$$item.shinyStat", None]}, None]}
                                        ]
                                    }
                                },
                                "in": {
                                    # Merge the new fields back into the item
                                    "$mergeObjects": [
                                        "$$item",
                                        {
                                            "group": "$$group",
                                            "type": "$$newType",

                                            # IMPORTANT: override shiny used downstream (grouping + "Shiny" label)
                                            "shiny": "$$effectiveShiny"
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
                    "group": {"$toLower": "$items.group"},
                    "shiny": "$items.shiny"
                },
                "itemsList": {
                    "$push": {
                        "itemType": "$items.itemType",
                        "amount": "$items.amount",
                        "name": "$items.name",
                        "type": "$items.type",
                        "rarity": "$items.rarity",
                        "shiny": "$items.shiny",
                        "shinyStat": "$items.shinyStat",
                        "icon": "$items.icon",
                        "tier": "$items.tier"
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

        # Group by region to assemble the final structure with itemsByGroup
        {
            "$group": {
                "_id": "$_id.region",
                "week": {"$first": week},
                "year": {"$first": year},
                "timestamp": {"$first": "$timestamp"},
                "itemsByGroup": {
                    "$push": {
                        "group": {
                            "$cond": {
                                "if": {"$eq": ["$_id.shiny", True]},
                                "then": "Shiny",
                                "else": {
                                    "$let": {
                                        "vars": {
                                            "groupLower": "$_id.group",
                                            "groupLength": {"$strLenCP": "$_id.group"}
                                        },
                                        "in": {
                                            "$concat": [
                                                {"$toUpper": {"$substr": ["$$groupLower", 0, 1]}},
                                                {
                                                    "$substr": [
                                                        "$$groupLower",
                                                        1,
                                                        {"$subtract": ["$$groupLength", 1]}
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
                                        {"case": {"$eq": ["$$item.group", "Shiny"]}, "then": 0},
                                        {"case": {"$eq": ["$$item.group", "Aspect"]}, "then": 1},
                                        {"case": {"$eq": ["$$item.group", "Mythic"]}, "then": 2},
                                        {"case": {"$eq": ["$$item.group", "Fabled"]}, "then": 3},
                                        {"case": {"$eq": ["$$item.group", "Legendary"]}, "then": 4},
                                        {"case": {"$eq": ["$$item.group", "Rare"]}, "then": 5},
                                        {"case": {"$eq": ["$$item.group", "Set"]}, "then": 6},
                                        {"case": {"$eq": ["$$item.group", "Unique"]}, "then": 7},
                                        {"case": {"$eq": ["$$item.group", "Tomes"]}, "then": 8},
                                        {"case": {"$eq": ["$$item.group", "Common"]}, "then": 9},
                                        {"case": {"$eq": ["$$item.group", "Misc"]}, "then": 10}
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
                        "sortBy": {"sortKey": 1}
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
                                        "shiny": "$$loot_item.shiny",
                                        "shinyStat": "$$loot_item.shinyStat",
                                        "icon": "$$loot_item.icon",
                                        "tier": "$$loot_item.tier"
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
            "$sort": {"region": 1}
        }
    ]

    cursor = get_collection(Collection.LOOT).aggregate(pipeline)
    return list(cursor)
