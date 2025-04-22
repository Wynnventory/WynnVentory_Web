from typing import List, Dict, Any

from modules.models.collection_types import Collection
from modules.repositories.base_pool_repo import BasePoolRepo, BasePoolAggregator
from modules.utils.time_validation import get_lootpool_week

# Initialize the base repository and aggregator with the LOOT collection type
_repo = BasePoolRepo(Collection.LOOT)
_aggregator = BasePoolAggregator(Collection.LOOT)

def save(pool: dict) -> None:
    """
    Insert or update a lootpool document for the given region/week/year,
    applying duplicate checks and timestamp logic.
    """
    _repo.save(pool)


def fetch_lootpool_raw() -> List[dict]:
    """
    Retrieve the raw lootpool documents for the current week/year.
    """
    return _repo.fetch_pool_raw()


def fetch_lootpool() -> List[Dict[str, Any]]:
    """
    Retrieve the processed lootpool items for the current week/year,
    grouped and sorted by region, group, and shiny status.
    """
    year, week = get_lootpool_week()

    # Define the configuration for the lootpool aggregation pipeline
    config = {
        'group_field_name': 'region_items',
        'item_field_name': 'loot_items',
        'group_branches': [
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
        'group_default': {
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
        },
        'sort_keys': {
            'Shiny': 0,
            'Aspect': 1,
            'Mythic': 2,
            'Fabled': 3,
            'Legendary': 4,
            'Rare': 5,
            'Set': 6,
            'Unique': 7,
            'Tomes': 8,
            'Common': 9,
            'Misc': 10
        },
        'additional_fields': {
            # Determine the new type for specific itemTypes
            "type": {
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
        'group_by_shiny': True
    }

    # Build and execute the pipeline
    pipeline = _aggregator.build_pipeline(year, week, config)
    return _aggregator.execute_pipeline(pipeline)
