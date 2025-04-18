from datetime import datetime, timedelta, timezone
from typing import List

from modules.db import get_collection
from modules.models.collection_types import Collection
from modules.utils.time_validation import get_lootpool_week, get_lootpool_week_for_timestamp


class LootpoolRepository:
    """
    Data-access layer for lootpool collections. Handles insertion (with duplicate checks)
    and retrieval (raw and processed) of lootpool documents.
    """

    def __init__(self) -> None:
        # Acquire the MongoDB collection for lootpool
        self.collection = get_collection(Collection.LOOT)

    def save(self, pool: dict) -> None:
        """ Insert or update a lootpool document for the given region/week/year,
        applying duplicate checks and timestamp logic.
        """

        # Compute week/year from the payload's collectionTime
        year, week = get_lootpool_week_for_timestamp(pool.get('collectionTime'))
        pool['week'] = week
        pool['year'] = year
        pool['timestamp'] = datetime.now(timezone.utc)

        # Build a filter for existing documents in same region/week/year
        region = pool.get('region')
        filter_q = {'region': region, 'week': week, 'year': year}
        existing = self.collection.find_one(filter_q)

        if existing:
            # Apply replacement rules
            existing_ts = existing['timestamp']
            age = datetime.now() - existing_ts
            new_items = pool.get('items', [])
            old_items = existing.get('items', [])

            has_more = len(new_items) > len(old_items)
            has_enough_and_stale = age > timedelta(hours=1) and len(new_items) >= len(old_items)
            is_older_week = (existing['year'], existing['week']) < (year, week)

            if has_more or has_enough_and_stale or is_older_week:
                # Replace the old document
                self.collection.delete_one(filter_q)
                self.collection.insert_one(pool)
            else:
                # Skip insertion
                return
        else:
            # No duplicate, insert fresh
            self.collection.insert_one(pool)

    def fetch_lootpool_raw(self) -> List[dict]:
        """ Retrieve the raw lootpool documents for the current week/year.
        """

        year, week = get_lootpool_week()
        cursor = self.collection.find(
            {'year': year, 'week': week},
            projection={'_id': 0}
        )
        return list(cursor)


    def fetch_lootpool(self) -> List[dict]:
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

        cursor = self.collection.aggregate(pipeline)
        return list(cursor)
