from datetime import timezone, datetime, timedelta
from typing import List, Dict, Any, Optional, Union

from pydantic.experimental import pipeline

from modules.db import get_collection
from modules.models.collection_types import Collection
from modules.repositories.base_pool_repo import BasePoolRepo, build_pool_pipeline
from modules.utils.time_validation import get_raidpool_week, get_current_gambit_day

# Initialize the base repository and aggregator with the RAID collection type
_repo = BasePoolRepo(Collection.RAID)

def save(pool: dict) -> None:
    """
    Insert or update a raidpool document for the given region/week/year,
    applying duplicate checks and timestamp logic.
    """
    _repo.save(pool)

def save_gambits(gambits: List[Dict]) -> None:
    """
    Insert or update a raidpool document for the given region/week/year,
    applying duplicate checks and timestamp logic.
    """
    collection = get_collection(Collection.GAMBIT)
    previous_reset, next_reset = get_current_gambit_day()

    previous_reset = previous_reset.replace(tzinfo=timezone.utc)
    next_reset = next_reset.replace(tzinfo=timezone.utc)

    filter_q = {"year": next_reset.year, "month": next_reset.month, "day": next_reset.day}

    gambit_day = {"playerName": gambits[0]["playerName"], "modVersion": gambits[0]["modVersion"]}

    for gambit in gambits:
        gambit.pop("playerName")
        gambit.pop("modVersion")

    collection_time = gambits[0].get('timestamp')
    collection_ts   = datetime.strptime(collection_time, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    gambit_day["timestamp"] = collection_ts
    gambit_day["year"] = next_reset.year
    gambit_day["month"] = next_reset.month
    gambit_day["day"] = next_reset.day
    gambit_day["gambits"] = gambits

    existing = collection.find_one(filter_q)
    if existing:
        existing_ts = existing.get('timestamp')
        if existing_ts.tzinfo is None:
            existing_ts = existing_ts.replace(tzinfo=timezone.utc)

        if not (collection_ts >= previous_reset and collection_ts < next_reset):
            return

        existing_ts_age = datetime.now(timezone.utc) - existing_ts

        existing_gambits = existing.get('gambits', [])
        has_more = len(gambits) > len(existing_gambits)
        has_enough_and_stale = existing_ts_age > timedelta(hours=1) and len(gambits) >= len(existing_gambits)

        if has_more or has_enough_and_stale:
            # Replace the old document
            collection.delete_one(filter_q)
            collection.insert_one(gambit_day)
    else:
        # No duplicate, insert fresh
        collection.insert_one(gambit_day)


def fetch_raidpools(
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
    coll = get_collection(Collection.RAID)
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
                                        "shiny": "$$item.shiny",
                                        "icon": "$$item.icon",
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

def fetch_gambits(
        year: int,
        month: int,
        day: int,
) -> dict:
    if not year or not month or not day:
        return {}

    filter_q = {"year": year, "month": month, "day": day}

    result = get_collection(Collection.GAMBIT).find_one(filter_q, projection={"_id": 0, "modVersion": 0, "playerName":0})

    if result is None:
        return {}

    return result