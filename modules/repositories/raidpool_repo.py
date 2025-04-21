from typing import List, Dict, Any

from modules.db import get_collection
from modules.models.collection_types import Collection
from modules.repositories.base_pool_repo import BasePoolRepo, BasePoolAggregator
from modules.utils.time_validation import get_raidpool_week

# Initialize the base repository and aggregator with the RAID collection type
_repo = BasePoolRepo(Collection.RAID)
_aggregator = BasePoolAggregator(Collection.RAID)

def save(pool: dict) -> None:
    """
    Insert or update a raidpool document for the given region/week/year,
    applying duplicate checks and timestamp logic.
    """
    _repo.save(pool)


def fetch_raidpool_raw() -> List[dict]:
    """
    Retrieve the raw raidpool documents for the current week/year.
    """
    return _repo.fetch_pool_raw()


def fetch_raidpool() -> List[Dict[str, Any]]:
    """
    Retrieve the processed raidpool items for the current week/year,
    grouped and sorted by region and group.
    """
    year, week = get_raidpool_week()

    # Define the configuration for the raidpool aggregation pipeline
    config = {
        'group_field_name': 'group_items',
        'item_field_name': 'loot_items',
        'group_branches': [
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
        'group_default': 'Other',
        'sort_keys': {
            'Aspects': 1,
            'Tomes': 2,
            'Gear': 3,
            'Misc': 4
        },
        'additional_fields': {
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
        },
        'group_by_shiny': False,
        'special_sort': {
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
        }
    }

    # Build and execute the pipeline
    pipeline = _aggregator.build_pipeline(year, week, config)
    return _aggregator.execute_pipeline(pipeline)
