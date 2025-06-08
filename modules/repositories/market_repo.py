import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta
from datetime import timezone, datetime
from typing import List, Dict, Any
from typing import Optional

from pymongo.errors import BulkWriteError

from modules.db import get_collection
from modules.models.collection_types import Collection as ColEnum

TIERED_TYPES = ["MaterialItem", "PowderItem", "AmplifierItem", "EmeraldPouchItem"]

def save(items: List[Dict[str, Any]]) -> None:
    """
    Insert multiple market items into the live collection,
    stamping each with the same UTC timestamp.
    Any duplicates (by hash_code) will be skipped,
    but the rest will succeed.
    """
    if not items:
        return

    ts = datetime.now(timezone.utc)
    for item in items:
        item['timestamp'] = ts

    market_collection = get_collection(ColEnum.MARKET_LISTINGS)

    try:
        res = market_collection.insert_many(items, ordered=False)
        inserted = len(res.inserted_ids)
    except BulkWriteError as bwe:
        # “nInserted” is how many made it in before duplicates/errors
        inserted = bwe.details.get("nInserted", 0)

    if inserted > 0:
        update_moving_averages(items=items)


def update_moving_averages(
        items: List[Dict[str, Any]],
        force_update: bool = False,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
) -> None:
    """
    Given a list of item stubs (each with 'name', 'tier', 'shiny_stat', and 'last_ts'),
    recalculate and upsert the moving‐average document only if:
      - force_update=True, OR
      - last_ts is newer than the stored average AND (optionally) within [start_date, end_date).
    """
    if not items:
        return

    averages_coll = get_collection(ColEnum.MARKET_AVERAGES)
    ts = datetime.now(timezone.utc)

    def worker(item: Dict[str, Any]) -> None:
        name = item['name']
        shiny = item.get('shiny_stat') is not None
        tier = item.get('tier')
        icon = item.get('icon')
        item_type = item.get('item_type')

        last_listing_ts: datetime = item.get('last_ts') if 'last_ts' in item else item.get('timestamp')
        if last_listing_ts:
            last_listing_ts = last_listing_ts.replace(tzinfo=timezone.utc)

        # If a date window was given, skip items outside it
        if start_date is not None and last_listing_ts < start_date:
            return
        if end_date is not None and last_listing_ts >= end_date:
            return

        filter_q: Dict[str, Any] = {
            'name': name,
            'tier': tier,
            'shiny': shiny
        }

        if not force_update:
            # Fetch existing average doc's timestamp
            existing = averages_coll.find_one(filter_q, {'timestamp': 1})
            existing_ts = existing.get('timestamp') if existing else None

            if existing_ts:
                existing_ts = existing_ts.replace(tzinfo=timezone.utc)

                if existing_ts >= last_listing_ts:
                    # No newer listings; skip recalculation
                    return

        # Recalculate only if listings are newer (or forced)
        price_data = calculate_listing_averages(
            item_name=name,
            shiny=shiny,
            tier=tier,
            start_date=start_date,
            end_date=end_date
        )

        if not price_data:
            return

        price_data.pop('_id', None)
        if start_date is not None:
            price_data['timestamp'] = last_listing_ts
        else:
            price_data['timestamp'] = ts
        price_data['icon'] = icon
        price_data['item_type'] = item_type

        averages_coll.update_one(
            filter_q,
            {'$set': price_data},
            upsert=True
        )

    with ThreadPoolExecutor() as executor:
        future_to_item = {executor.submit(worker, it): it for it in items}
        for fut in as_completed(future_to_item):
            item = future_to_item[fut]
            if fut.exception():
                logging.error(f"Error updating moving average for {item.get('name')} with exception {fut.exception()}")


def update_moving_averages_complete(force_update: bool = False,
                                    start_date: datetime = None,
                                    end_date: datetime = None,
) -> None:
    """
    Scan MARKET_LISTINGS via an aggregation that returns one document per unique
    (name, tier, shiny‐flag) combination, along with the most recent listing timestamp.
    Then call update_moving_averages(...) only for those whose listings are newer
    than the saved average.
    """
    listing_coll = get_collection(ColEnum.MARKET_LISTINGS)

    match_stage: Dict[str, Any] = {}
    if start_date is not None or end_date is not None:
        ts_filter: Dict[str, Any] = {}
        if start_date is not None:
            ts_filter["$gte"] = start_date
        if end_date is not None:
            ts_filter["$lt"] = end_date

        match_stage["timestamp"] = ts_filter

    pipeline: List[Dict[str, Any]] = []
    if match_stage:
        pipeline.append({"$match": match_stage})

    # Pipeline:
    # 1) Project name, tier, shiny‐flag, and timestamp
    # 2) Group by {name, tier, shiny}, taking the max timestamp
    pipeline.extend([
        {
            "$project": {
                "_id": 0,
                "name": 1,
                "tier": 1,
                "shiny": { "$cond": [{ "$ne": ["$shiny_stat", None] }, True, False] },
                "icon": 1,
                "item_type": 1,
                "timestamp": 1
            }
        },
        {
            "$group": {
                "_id": {
                    "name": "$name",
                    "tier": "$tier",
                    "shiny": "$shiny",
                    "icon": "$icon",
                    "item_type": "$item_type"
                },
                "last_ts": { "$max": "$timestamp" }
            }
        }
    ])

    cursor = listing_coll.aggregate(pipeline, allowDiskUse=True)

    unique_items: List[Dict[str, Any]] = []
    for entry in cursor:
        key = entry["_id"]

        # Reconstruct a stub. Only shiny_stat != None when shiny_flag is True.
        shiny_stat = True if key["shiny"] else None

        unique_items.append({
            "name": key["name"],
            "tier": key["tier"],
            "shiny_stat": shiny_stat,
            "icon": key.get("icon"),
            "item_type": key["item_type"],
            "last_ts": entry["last_ts"]
        })

    if unique_items:
        update_moving_averages(items=unique_items, force_update=force_update, start_date=start_date, end_date=end_date)


def get_trade_market_item_listings(
        item_name: Optional[str] = None,
        shiny: Optional[bool] = None,
        unidentified: Optional[bool] = None,
        rarity: Optional[str] = None,
        tier: Optional[int] = None,
        item_type: Optional[str] = None,
        page: Optional[int] = 1,
        page_size: Optional[int] = 50,
) -> Dict[str, Any]:
    """
    Retrieve market entries, optionally filtering by:
      - name
      - shiny status (if shiny is True/False; if None, don't filter by shiny)
      - tier (for MaterialItem or globally if no name/type)
      - item_type
    """
    skip = (page - 1) * page_size

    query_filter: Dict[str, Any] = {}

    # only filter on shiny_stat if shiny was explicitly passed
    if shiny is not None:
        shiny_op = '$ne' if shiny else '$eq'
        query_filter['shiny_stat'] = {shiny_op: None}

    if unidentified is not None:
        query_filter['unidentified'] = {"$eq": unidentified}

    if rarity is not None:
        if rarity.lower() == "normal":
            escaped = re.escape(rarity)
            regex = {"$regex": f"^{escaped}$", "$options": "i"}
            query_filter["$or"] = [
                {"rarity": regex},
                {"rarity": {"$eq": None}}
            ]

        else:
            escaped = re.escape(rarity)
            query_filter["rarity"] = {
                "$regex": f"^{escaped}$",
                "$options": "i"
            }

    # 1) NAME branch
    if item_name:
        query_filter['name'] = {
            '$regex': f'.*{re.escape(item_name)}.*',
            '$options': 'i'
        }

        if item_type is not None:
            # explicit single-type + optional tier
            query_filter['item_type'] = item_type
            if tier is not None and item_type in TIERED_TYPES:
                query_filter['tier'] = tier

        else:
            # fallback to original OR logic
            if tier is not None:
                query_filter['$or'] = [
                    {'item_type': {'$nin': TIERED_TYPES}},
                    {'item_type': {'$in': TIERED_TYPES}, 'tier': tier}
                ]

    # 2) NO-NAME branch
    else:
        if item_type is not None:
            query_filter['item_type'] = item_type
            if tier is not None and item_type in TIERED_TYPES:
                query_filter['tier'] = tier
        else:
            if tier is not None:
                query_filter['item_type'] = {'$in': TIERED_TYPES}
                query_filter['tier']      = tier


    coll = get_collection(ColEnum.MARKET_LISTINGS)
    total = coll.count_documents(query_filter)

    cursor = coll.find(
        filter=query_filter,
        projection={
            '_id': 0,
            'player_name': 0
        }
    ).sort('timestamp', -1).skip(skip).limit(page_size)

    items = list(cursor)

    return {
        'page': (skip // page_size) + 1,
        'page_size': page_size,
        'count': len(items),
        'total': total,
        'items': items
    }


def calculate_listing_averages(
        item_name: str,
        shiny: bool = False,
        tier: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Compute price statistics (min, max, avg, mid-80%) for identified and unidentified listings,
    taking each 'amount' into account (so a listing of amount=4 counts as four data points).
    Returns a dict of:
      - lowest_price, highest_price, average_price, average_mid_80_percent_price
      - unidentified_average_price, unidentified_average_mid_80_percent_price
      - total_count, unidentified_count
      - name
    """
    shiny_stat = '$ne' if shiny else '$eq'
    query_filter: Dict[str, Any] = {'name': item_name, 'shiny_stat': {shiny_stat: None}, '$or': [
        {'item_type': {'$nin': TIERED_TYPES}},
        {'item_type': {'$in': TIERED_TYPES}, 'tier': tier}
    ]}

    if start_date is not None or end_date is not None:
        ts_filter: Dict[str, Any] = {}
        if start_date is not None:
            ts_filter['$gte'] = start_date
        if end_date is not None:
            ts_filter['$lt'] = end_date
        query_filter['timestamp'] = ts_filter

    # 2) build pipeline
    pipeline = [
        # 1) Only the docs we care about, in price order
        {'$match': query_filter},
        {'$addFields': {'unitIndex': {'$range': [0, '$amount']}}},
        {'$unwind': '$unitIndex'},
        {'$sort': {'listing_price': 1}},

        # 2) Single pass grouping
        {'$group': {
            '_id': None,
            # pull tier & name from the first doc in sort order
            'tier': {'$first': '$tier'},
            'name': {'$first': '$name'},

            # all identified prices in one array
            'identifiedPrices': {
                '$push': {
                    '$cond': [
                        {'$ne': ['$unidentified', True]},
                        '$listing_price',
                        '$$REMOVE'
                    ]
                }
            },
            # all unidentified prices in another
            'unidentifiedPrices': {
                '$push': {
                    '$cond': [
                        {'$eq': ['$unidentified', True]},
                        '$listing_price',
                        '$$REMOVE'
                    ]
                }
            },

            # counts & sums & mins & maxes
            'identifiedCount': {'$sum': {'$cond': [{'$ne': ['$unidentified', True]}, 1, 0]}},
            'unidentifiedCount': {'$sum': {'$cond': [{'$eq': ['$unidentified', True]}, 1, 0]}},
            'identifiedMin': {'$min': {'$cond': [{'$ne': ['$unidentified', True]}, '$listing_price', None]}},
            'identifiedMax': {'$max': {'$cond': [{'$ne': ['$unidentified', True]}, '$listing_price', None]}},
            'identifiedAvg': {'$avg': {'$cond': [{'$ne': ['$unidentified', True]}, '$listing_price', None]}},
            'unidentifiedAvg': {'$avg': {'$cond': [{'$eq': ['$unidentified', True]}, '$listing_price', None]}}
        }},

        # 3) Final projection
        {'$project': {
            'tier': 1,
            'name': 1,

            'lowest_price': {'$round': ['$identifiedMin', 2]},
            'highest_price': {'$round': ['$identifiedMax', 2]},
            'average_price': {'$round': ['$identifiedAvg', 2]},

            'total_count': {
                '$add': ['$identifiedCount', '$unidentifiedCount']
            },
            'unidentified_count': '$unidentifiedCount',
            'unidentified_average_price': {'$round': ['$unidentifiedAvg', 2]},

            'average_mid_80_percent_price': {
                '$round': [
                    {
                        '$cond': [
                            {'$gt': [{'$size': '$identifiedPrices'}, 2]},
                            {'$avg': {
                                '$slice': [
                                    '$identifiedPrices',
                                    {'$ceil': {'$multiply': [{'$size': '$identifiedPrices'}, 0.1]}},
                                    {
                                        '$subtract': [
                                            {'$size': '$identifiedPrices'},
                                            {'$multiply': [
                                                2,
                                                {'$ceil': {'$multiply': [{'$size': '$identifiedPrices'}, 0.1]}}
                                            ]}
                                        ]
                                    }
                                ]
                            }},
                            {'$avg': '$identifiedPrices'}
                        ]
                    },
                    2
                ]
            },

            # mid-80-percent for unidentified
            'unidentified_average_mid_80_percent_price': {
                '$round': [
                    {
                        '$cond': [
                            {'$gt': [{'$size': '$unidentifiedPrices'}, 2]},
                            {'$avg': {
                                '$slice': [
                                    '$unidentifiedPrices',
                                    {'$ceil': {'$multiply': [{'$size': '$unidentifiedPrices'}, 0.1]}},
                                    {
                                        '$subtract': [
                                            {'$size': '$unidentifiedPrices'},
                                            {'$multiply': [
                                                2,
                                                {'$ceil': {'$multiply': [{'$size': '$unidentifiedPrices'}, 0.1]}}
                                            ]}
                                        ]
                                    }
                                ]
                            }},
                            {'$avg': '$unidentifiedPrices'}
                        ]
                    },
                    2
                ]
            }
        }}
    ]

    cursor = get_collection(ColEnum.MARKET_LISTINGS).aggregate(pipeline)
    try:
        stats = cursor.next()
    except StopIteration:
        return {}

    return stats


def get_trademarket_item_price(
        item_name: str,
        shiny: bool = False,
        tier: Optional[int] = None
) -> Dict[str, Any]:
    if tier and tier <= 0:
        tier = None

    filter_q = {
        'name': item_name,
        'tier': tier,
        'shiny': shiny
    }

    result = get_collection(ColEnum.MARKET_AVERAGES).find_one(filter_q, {"_id": False})

    if result:
        return result
    else:
        return {}


def get_price_history(
        item_name: str,
        shiny: bool = False,
        tier: Optional[int] = None,
        start_date: datetime = None,
        end_date: datetime = None,
        default_days: int = 7
) -> List[Dict[str, Any]]:
    """
    Retrieve the price history of an item over a given date range.
    """
    lagged_now = datetime.now(timezone.utc) - timedelta(days=1)

    # 2) If end_date wasn’t given, use lagged_now
    end_date = end_date or lagged_now
    end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)

    # 3) If start_date wasn’t given, backfill to a full default_days window
    start_date = start_date or (end_date - timedelta(days=default_days))
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

    # 4) Inclusive end_date via half-open interval
    exclusive_end = end_date + timedelta(days=1)

    query_filter: Dict[str, Any] = {
        'name': item_name,
        'shiny': shiny,
        '$or': [
            {'item_type': {'$nin': TIERED_TYPES}},
            {'item_type': {'$in': TIERED_TYPES}, 'tier': tier}
        ],
        'timestamp': {
            '$gte': start_date,
            '$lt': exclusive_end
        }
    }

    cursor = get_collection(ColEnum.MARKET_ARCHIVE).find(
        filter=query_filter,
        sort=[('timestamp', 1)],
        projection={'_id': 0}
    )
    return list(cursor)


def get_historic_average(
        item_name: str,
        shiny: bool = False,
        tier: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        default_days: int = 7
) -> Dict[str, Any]:
    """
    Compute average stats for an item over a date range.
    If neither start_date nor end_date is provided, uses the last `default_days`.
    If only one is provided, fills the other to span a `default_days` window
    (or up to now for the end).
    """
    # 1) Shift “now” back by default_days once
    lagged_now = datetime.now(timezone.utc) - timedelta(days=1)

    # 2) If end_date wasn’t given, use lagged_now
    end_date = end_date or lagged_now
    end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)

    # 3) If start_date wasn’t given, backfill to a full default_days window
    start_date = start_date or (end_date - timedelta(days=default_days))
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

    # 4) Inclusive end_date via half-open interval
    exclusive_end = end_date + timedelta(days=1)


    # base query
    query: Dict[str, Any] = {
        'name': item_name,
        'shiny': shiny,
        '$or': [
            {'item_type': {'$nin': TIERED_TYPES}},
            {'item_type': {'$in': TIERED_TYPES}, 'tier': tier}
        ],
        'timestamp': {
            '$gte': start_date,
            '$lt': exclusive_end
        }
    }

    pipeline = [
        {'$match': query},
        {'$group': {
            '_id': None,
            'name': {'$first': '$name'},
            'tier': {'$first': '$tier'},
            'document_count': {'$sum': 1},

            # averages over the matched docs
            'lowest_price': {'$avg': '$lowest_price'},
            'highest_price': {'$avg': '$highest_price'},
            'average_price': {'$avg': '$average_price'},

            'total_count': {'$sum': '$total_count'},
            'avg_mid80': {'$avg': '$average_mid_80_percent_price'},
            'unidentified_avg': {'$avg': '$unidentified_average_price'},
            'unidentified_mid80_avg': {'$avg': '$unidentified_average_mid_80_percent_price'},
            'unidentified_count': {'$sum': '$unidentified_count'}
        }},
        {'$project': {
            '_id': 0,
            'name': 1,
            'tier': 1,
            'document_count': 1,
            'lowest_price': {'$round': ['$lowest_price', 2]},
            'highest_price': {'$round': ['$highest_price', 2]},
            'average_price': {'$round': ['$average_price', 2]},
            'total_count': {'$toInt': '$total_count'},
            'average_mid_80_percent_price': {'$round': ['$avg_mid80', 2]},
            'unidentified_average_price': {'$round': ['$unidentified_avg', 2]},
            'unidentified_average_mid_80_percent_price': {'$round': ['$unidentified_mid80_avg', 2]},
            'unidentified_count': {'$toInt': '$unidentified_count'}
        }}
    ]

    result = list(
        get_collection(ColEnum.MARKET_ARCHIVE)
        .aggregate(pipeline, allowDiskUse=False)
    )
    return result[0] if result else {}


def get_all_items_ranking(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        default_days: int = 7
) -> List[Dict[str, Any]]:
    """
    Retrieve a ranking of items based on archived price data,
    automatically lagged by `default_days + 1` so the latest
    document is always `default_days` days in the past.
    """

    # 1) Shift “now” back by default_days once
    lagged_now = datetime.now(timezone.utc) - timedelta(days=1)

    # 2) If end_date wasn’t given, use lagged_now
    end_date = end_date or lagged_now
    end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)

    # 3) If start_date wasn’t given, backfill to a full default_days window
    start_date = start_date or (end_date - timedelta(days=default_days))
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

    # 4) Inclusive end_date via half-open interval
    exclusive_end = end_date + timedelta(days=1)

    date_filter: Dict[str, Any] = {
        'timestamp': {
            '$gte': start_date,
            '$lt': exclusive_end
        },
        'shiny_stat': {'$eq': None}
    }

    pipeline: List[Dict[str, Any]] = [{'$match': date_filter}]

    # 2) Group by item name and compute aggregates
    pipeline.append({
        '$group': {
            '_id': '$name',
            'lowest_price': {'$min': '$lowest_price'},
            'highest_price': {'$max': '$highest_price'},
            'average_price': {'$avg': '$average_price'},
            'average_total_count': {'$avg': '$total_count'},
            'average_unidentified_count': {'$avg': '$unidentified_count'},
            'average_mid_80_percent_price': {'$avg': '$average_mid_80_percent_price'},
            'unidentified_average_mid_80_percent_price': {
                '$avg': '$unidentified_average_mid_80_percent_price'
            },
            'total_count': {'$sum': '$total_count'},
            'unidentified_count': {'$sum': '$unidentified_count'}
        }
    })

    # 3) Sort descending by average price
    pipeline.append({'$sort': {'average_price': -1}})

    # run the aggregation
    cursor = get_collection(ColEnum.MARKET_ARCHIVE).aggregate(pipeline)

    # 4) Enumerate and add 'rank'
    ranked = []
    for idx, doc in enumerate(cursor, start=1):
        item = {
            'rank': idx,
            'name': doc['_id'],
            **{k: doc[k] for k in doc if k != '_id'}
        }
        ranked.append(item)

    return ranked
