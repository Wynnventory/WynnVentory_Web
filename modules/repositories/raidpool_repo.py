from typing import List, Dict, Any, Optional, Union

from modules.db import get_collection
from modules.models.collection_types import Collection
from modules.repositories.base_pool_repo import BasePoolRepo, build_pool_pipeline
from modules.utils.time_validation import get_raidpool_week

# Initialize the base repository and aggregator with the RAID collection type
_repo = BasePoolRepo(Collection.RAID)

def save(pool: dict) -> None:
    """
    Insert or update a raidpool document for the given region/week/year,
    applying duplicate checks and timestamp logic.
    """
    _repo.save(pool)

def fetch_raidpools(year: Optional[int] = None, week: Optional[int] = None) -> Union[Dict, List[Dict]]:
    """
    If both year and week are passed, returns a single dict (or {} if none found).
    If neither is passed, returns a List of every year/week doc.
    """
    pipeline = build_pool_pipeline(year, week)
    cursor = get_collection(Collection.RAID).aggregate(pipeline)

    # single‐object case
    if year is not None and week is not None:
        try:
            return cursor.next()
        except StopIteration:
            return {}

    # “all” case
    return list(cursor)


# OLD GROUPED FORMAT
def fetch_raidpool():
    year, week = get_raidpool_week()
    pipeline = [
        # Match documents for the given week and year
        {
            "$match": {
                "week": week,
                "year": year
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
                "week": { "$first": week },
                "year": { "$first": year },
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
    ]

    cursor = get_collection(Collection.RAID).aggregate(pipeline)
    return list(cursor)
