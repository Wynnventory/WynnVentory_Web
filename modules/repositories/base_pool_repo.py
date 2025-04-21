from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple, Dict, Any, Callable

from modules.db import get_collection
from modules.models.collection_types import Collection
from modules.utils.time_validation import get_lootpool_week, get_lootpool_week_for_timestamp, get_raidpool_week


class BasePoolRepo:
    """
    Base repository class for lootpool and raidpool operations.
    Provides common functionality for saving and retrieving pool data.
    """

    def __init__(self, collection_type: Collection):
        self.collection_type = collection_type

    def save(self, pool: dict) -> None:
        """
        Insert or update a pool document for the given region/week/year,
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
        collection = get_collection(self.collection_type)
        existing = collection.find_one(filter_q)

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
                collection.delete_one(filter_q)
                collection.insert_one(pool)
            else:
                # Skip insertion
                return
        else:
            # No duplicate, insert fresh
            collection.insert_one(pool)

    def fetch_pool_raw(self) -> List[dict]:
        """
        Retrieve the raw pool documents for the current week/year.
        """
        year, week = self._get_week_year()
        cursor = get_collection(self.collection_type).find(
            {'year': year, 'week': week},
            projection={'_id': 0}
        )
        return list(cursor)

    def _get_week_year(self) -> Tuple[int, int]:
        """
        Get the appropriate week and year based on collection type.
        """
        if self.collection_type == Collection.RAID:
            return get_raidpool_week()
        else:
            return get_lootpool_week()


class BasePoolAggregator:
    """
    Base class for building aggregation pipelines for lootpool and raidpool.
    Provides a common framework with hooks for specific differences.
    """

    def __init__(self, collection_type: Collection):
        self.collection_type = collection_type

    def build_pipeline(self, year: int, week: int, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Build an aggregation pipeline for the given parameters.

        Args:
            year: The year to filter by
            week: The week to filter by
            config: Configuration parameters for the pipeline
                - group_field_name: The name of the field in the final output (e.g., 'region_items', 'group_items')
                - item_field_name: The name of the field for items in the output (e.g., 'loot_items')
                - group_branches: The branches for the $switch operator to determine item groups
                - group_default: The default value for the group field
                - sort_keys: The sort keys for groups
                - additional_fields: Additional fields to add to each item
                - group_by_shiny: Whether to group by shiny status
                - special_sort: Special sorting logic for specific groups

        Returns:
            A MongoDB aggregation pipeline as a list of stages
        """
        # Extract configuration parameters with defaults
        group_field_name = config.get('group_field_name', 'region_items')
        item_field_name = config.get('item_field_name', 'loot_items')
        group_branches = config.get('group_branches', [])
        group_default = config.get('group_default', 'Other')
        sort_keys = config.get('sort_keys', {})
        additional_fields = config.get('additional_fields', {})
        group_by_shiny = config.get('group_by_shiny', False)
        special_sort = config.get('special_sort', None)

        # Start with the match stage
        pipeline = [
            # Match documents for the given week and year
            {
                "$match": {
                    "week": week,
                    "year": year
                }
            }
        ]

        # Add fields to each item
        add_fields_stage = {
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
                                            "branches": group_branches,
                                            "default": group_default
                                        }
                                    }
                                },
                                additional_fields
                            ]
                        }
                    }
                }
            }
        }
        pipeline.append(add_fields_stage)

        # Unwind the items array
        pipeline.append({"$unwind": "$items"})

        # Group items by region and other fields
        group_id = {"region": "$region", "group": "$items.group"}
        if group_by_shiny:
            group_id["shiny"] = "$items.shiny"

        group_stage = {
            "$group": {
                "_id": group_id,
                "itemsList": {"$push": "$items"},
                "timestamp": {"$first": "$timestamp"}
            }
        }
        pipeline.append(group_stage)

        # Add sort keys and sort the items
        if sort_keys:
            # Add sort keys to items
            pipeline.append({
                "$addFields": {
                    "itemsList": {
                        "$map": {
                            "input": "$itemsList",
                            "as": "item",
                            "in": {
                                "$mergeObjects": [
                                    "$$item",
                                    {
                                        "sortKey": {
                                            "$switch": {
                                                "branches": [
                                                    {"case": {"$eq": ["$$item.rarityLower", k]}, "then": v}
                                                    for k, v in sort_keys.items()
                                                ],
                                                "default": len(sort_keys) + 1
                                            }
                                        }
                                    }
                                ]
                            }
                        }
                    }
                }
            })

            # Sort items by sort key and name
            pipeline.append({
                "$addFields": {
                    "itemsList": {
                        "$sortArray": {
                            "input": "$itemsList",
                            "sortBy": {"sortKey": 1, "name": 1}
                        }
                    }
                }
            })

        # Group by region
        group_by_region_stage = {
            "$group": {
                "_id": "$_id.region",
                "week": {"$first": week},
                "year": {"$first": year},
                "timestamp": {"$first": "$timestamp"},
                "itemsByGroup": {
                    "$push": {
                        "group": self._get_group_expression(group_by_shiny),
                        "items": "$itemsList"
                    }
                }
            }
        }
        pipeline.append(group_by_region_stage)

        # Add group sort keys and sort the groups
        if sort_keys:
            pipeline.append({
                "$addFields": {
                    "itemsByGroup": {
                        "$map": {
                            "input": "$itemsByGroup",
                            "as": "groupItem",
                            "in": {
                                "$mergeObjects": [
                                    "$$groupItem",
                                    {
                                        "groupSortKey": {
                                            "$switch": {
                                                "branches": [
                                                    {"case": {"$eq": ["$$groupItem.group", k]}, "then": v}
                                                    for k, v in sort_keys.items()
                                                ],
                                                "default": len(sort_keys) + 1
                                            }
                                        }
                                    }
                                ]
                            }
                        }
                    }
                }
            })

            # Sort groups by sort key
            pipeline.append({
                "$addFields": {
                    "itemsByGroup": {
                        "$sortArray": {
                            "input": "$itemsByGroup",
                            "sortBy": {"groupSortKey": 1}
                        }
                    }
                }
            })

        # Apply special sorting if provided
        if special_sort:
            pipeline.append(special_sort)

        # Project the final output
        project_stage = {
            "$project": {
                "_id": 0,
                "region": "$_id",
                "week": 1,
                "year": 1,
                "timestamp": 1,
                group_field_name: {
                    "$map": {
                        "input": "$itemsByGroup",
                        "as": "groupItem",
                        "in": {
                            "group": "$$groupItem.group",
                            item_field_name: {
                                "$map": {
                                    "input": "$$groupItem.items",
                                    "as": "item",
                                    "in": {
                                        "name": "$$item.name",
                                        "type": "$$item.type",
                                        "rarity": "$$item.rarity",
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
        }
        pipeline.append(project_stage)

        # Sort by region
        pipeline.append({"$sort": {"region": 1}})

        return pipeline

    def _get_group_expression(self, group_by_shiny: bool) -> Dict[str, Any]:
        """
        Get the expression for determining the group name in the final output.

        Args:
            group_by_shiny: Whether to include shiny status in grouping

        Returns:
            A MongoDB expression for determining the group name
        """
        if group_by_shiny:
            return {
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
            }
        else:
            return "$_id.group"

    def execute_pipeline(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute the aggregation pipeline on the appropriate collection.

        Args:
            pipeline: The MongoDB aggregation pipeline to execute

        Returns:
            The results of the aggregation as a list of dictionaries
        """
        cursor = get_collection(self.collection_type).aggregate(pipeline)
        return list(cursor)
