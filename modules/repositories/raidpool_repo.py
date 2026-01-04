import logging
import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Union

UTC = timezone.utc

from modules.db import get_collection
from modules.models.collection_types import Collection
from modules.repositories.base_pool_repo import BasePoolRepo, build_pool_pipeline
from modules.utils.time_validation import get_raidpool_week, get_current_gambit_day, parse_utc_timestamp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s"
)

logger = logging.getLogger(__name__)

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
    Insert or update a gambit document for the UTC gambit day window,
    applying duplicate checks and timestamp logic.
    """
    if not gambits:
        return

    collection = get_collection(Collection.GAMBIT)
    previous_reset, next_reset = get_current_gambit_day()  # must return UTC-aware datetimes

    # Safety: enforce aware UTC
    if previous_reset.tzinfo is None or next_reset.tzinfo is None:
        raise RuntimeError("get_current_gambit_day() must return timezone-aware UTC datetimes")

    filter_q = {"year": next_reset.year, "month": next_reset.month, "day": next_reset.day}

    gambit_day = {
        "playerName": gambits[0]["playerName"],
        "modVersion": gambits[0]["modVersion"],
    }

    # Parse incoming timestamps strictly and filter by the gambit window
    valid_gambits = []
    first_valid_ts = None

    for gambit in gambits:
        # Remove repeated fields from individual entries
        gambit.pop("playerName", None)
        gambit.pop("modVersion", None)

        ts_str = gambit.get("timestamp")
        if ts_str is None:
            continue

        try:
            ts = parse_utc_timestamp(ts_str)
            if previous_reset <= ts < next_reset:
                valid_gambits.append(gambit)
                if first_valid_ts is None:
                    first_valid_ts = ts
        except (ValueError, TypeError):
            continue

    if not valid_gambits:
        return

    gambit_day["timestamp"] = first_valid_ts
    gambit_day["year"] = next_reset.year
    gambit_day["month"] = next_reset.month
    gambit_day["day"] = next_reset.day
    gambit_day["gambits"] = valid_gambits

    existing = collection.find_one(filter_q)
    if existing:
        existing_ts = existing.get("timestamp")
        if existing_ts is None:
            # If somehow missing, treat as replaceable
            existing_ts = datetime.fromtimestamp(0, tz=UTC)

        if not hasattr(existing_ts, 'tzinfo'):
            raise TypeError(f"Existing timestamp is not a datetime: {type(existing_ts)!r}")

        if existing_ts.tzinfo is None:
            # strict: do not silently assume UTC
            raise ValueError("Existing document has naive 'timestamp' (must be UTC-aware)")

        existing_ts = existing_ts.astimezone(UTC)

        existing_ts_age = datetime.now(UTC) - existing_ts

        existing_gambits = existing.get("gambits", [])
        has_more = len(gambits) > len(existing_gambits)
        has_enough_and_stale = existing_ts_age > timedelta(hours=1) and len(gambits) >= len(existing_gambits)

        if has_more or has_enough_and_stale:
            collection.delete_one(filter_q)
            collection.insert_one(gambit_day)
    else:
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
    start_time = time.time()
    logger.info(f"fetch_raidpools - Started with parameters: year={year}, week={week}, "
                f"page={page}, page_size={page_size}, skip={skip}")
    
    coll = get_collection(Collection.RAID)
    pipeline = build_pool_pipeline(year, week)
    logger.info(f"fetch_raidpools - Pipeline built for year={year}, week={week}")
    
    # 1) Single‐object case
    if year is not None and week is not None:
        logger.info(f"fetch_raidpools - Executing single-object query for year={year}, week={week}")
        query_start_time = time.time()
        
        cursor = coll.aggregate(pipeline)
        
        try:
            result = cursor.next()
            
            query_duration = time.time() - query_start_time
            logger.info(f"fetch_raidpools - Single-object query completed in {query_duration:.3f}s")
            
            total_duration = time.time() - start_time
            logger.info(f"fetch_raidpools - Total execution time: {total_duration:.3f}s")
            
            return result
        except StopIteration:
            query_duration = time.time() - query_start_time
            logger.info(f"fetch_raidpools - Single-object query completed in {query_duration:.3f}s with no result")
            
            total_duration = time.time() - start_time
            logger.info(f"fetch_raidpools - Total execution time: {total_duration:.3f}s")
            
            return {}

    paged_pipeline = pipeline + [
        {"$skip": skip},
        {"$limit": page_size}
    ]
    logger.info(f"fetch_raidpools - Executing paginated query with skip={skip}, limit={page_size}")
    
    query_start_time = time.time()
    
    # 2) Paginated “all” case
    results = list(coll.aggregate(paged_pipeline))
    
    query_duration = time.time() - query_start_time
    logger.info(f"fetch_raidpools - Paginated query completed in {query_duration:.3f}s, retrieved {len(results)} pools")
    
    total_duration = time.time() - start_time
    logger.info(f"fetch_raidpools - Total execution time: {total_duration:.3f}s")

    return {
        "page": page,
        "page_size": page_size,
        "count": len(results),
        "pools": results
    }


# OLD GROUPED FORMAT
def fetch_raidpool():
    start_time = time.time()
    logger.info("fetch_raidpool - Started")
    
    year, week = get_raidpool_week()
    logger.info(f"fetch_raidpool - Determined raidpool week: year={year}, week={week}")
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
                                                    "case": {"$eq": ["$$item.itemType", "AspectItem"]},
                                                    "then": "Aspects"
                                                },
                                                {
                                                    "case": {"$eq": ["$$item.itemType", "GearItem"]},
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
                                                        "$in": ["$$item.itemType",
                                                                ["PowderItem", "EmeraldItem", "AmplifierItem"]]
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
                                            "if": {"$ne": ["$$item.rarity", None]},
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
                                                                {"$strLenCP": "$$item.rarity"}
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
                "timestamp": {"$first": "$timestamp"}
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
                                                {"case": {"$eq": ["$$item.rarityLower", "mythic"]}, "then": 1},
                                                {"case": {"$eq": ["$$item.rarityLower", "fabled"]}, "then": 2},
                                                {"case": {"$eq": ["$$item.rarityLower", "legendary"]}, "then": 3},
                                                {"case": {"$eq": ["$$item.rarityLower", "rare"]}, "then": 4},
                                                {"case": {"$eq": ["$$item.rarityLower", "unique"]}, "then": 5},
                                                {"case": {"$eq": ["$$item.rarityLower", "common"]}, "then": 6},
                                                {"case": {"$eq": ["$$item.rarityLower", "set"]}, "then": 7}
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
                "week": {"$first": week},
                "year": {"$first": year},
                "timestamp": {"$first": "$timestamp"},
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
                                                {"case": {"$eq": ["$$item.group", "Aspects"]}, "then": 1},
                                                {"case": {"$eq": ["$$item.group", "Tomes"]}, "then": 2},
                                                {"case": {"$eq": ["$$item.group", "Gear"]}, "then": 3},
                                                {"case": {"$eq": ["$$item.group", "Misc"]}, "then": 4}
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
                        "sortBy": {"groupSortKey": 1}
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
                                            {"$eq": ["$$groupItem.group", "Aspects"]},
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
            "$sort": {"region": 1}
        }
    ]

    logger.info("fetch_raidpool - Executing complex aggregation pipeline")
    query_start_time = time.time()
    
    cursor = get_collection(Collection.RAID).aggregate(pipeline)
    result = list(cursor)
    
    query_duration = time.time() - query_start_time
    logger.info(f"fetch_raidpool - Aggregation completed in {query_duration:.3f}s")
    
    if result:
        logger.info(f"fetch_raidpool - Retrieved {len(result)} raidpool documents")
    else:
        logger.info("fetch_raidpool - No results found")
    
    total_duration = time.time() - start_time
    logger.info(f"fetch_raidpool - Total execution time: {total_duration:.3f}s")
    
    return result


def fetch_gambits(
        year: int,
        month: int,
        day: int,
) -> dict:
    start_time = time.time()
    logger.info(f"fetch_gambits - Started with parameters: year={year}, month={month}, day={day}")
    
    if not year or not month or not day:
        logger.info("fetch_gambits - Missing required parameters, returning empty result")
        return {}

    filter_q = {"year": year, "month": month, "day": day}
    logger.info(f"fetch_gambits - Query filter: {filter_q}")
    
    query_start_time = time.time()
    logger.info("fetch_gambits - Executing find_one query")
    
    result = get_collection(Collection.GAMBIT).find_one(filter_q,
                                                        projection={"_id": 0, "modVersion": 0, "playerName": 0})
    
    query_duration = time.time() - query_start_time
    logger.info(f"fetch_gambits - Query completed in {query_duration:.3f}s")

    if result is None:
        logger.info("fetch_gambits - No result found")
        total_duration = time.time() - start_time
        logger.info(f"fetch_gambits - Total execution time: {total_duration:.3f}s")
        return {}
    
    if "gambits" in result:
        logger.info(f"fetch_gambits - Retrieved {len(result['gambits'])} gambits")
    
    total_duration = time.time() - start_time
    logger.info(f"fetch_gambits - Total execution time: {total_duration:.3f}s")
    
    return result
