from datetime import timedelta
from datetime import timezone, datetime
from typing import List, Dict, Any
from typing import Optional

from pymongo.errors import BulkWriteError

from modules.db import get_collection
from modules.models.collection_types import Collection as ColEnum


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
    for it in items:
        it['timestamp'] = ts

    collection = get_collection(ColEnum.MARKET)
    try:
        # ordered=False => fire off all inserts;
        # duplicate-key errors don’t stop the rest.
        collection.insert_many(items, ordered=False)
    except BulkWriteError as bwe:
        # Optionally inspect bwe.details['writeErrors'] for logging,
        # but you can safely ignore duplicate-key errors here.
        pass


def get_trade_market_item(
    item_name: str,
    shiny: bool = False,
    tier: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve all market entries for an item by name.
    """
    shiny_stat = '$ne' if shiny else '$eq'
    query_filter: Dict[str, Any] = {'name': item_name, 'shiny_stat': {shiny_stat: None}, '$or': [
        {'item_type': {'$in': ['GearItem', 'IngredientItem']}},
        {'item_type': 'MaterialItem', 'tier': tier}
    ]}

    cursor = get_collection(ColEnum.MARKET).find(
        filter=query_filter,
        projection={'_id': 0}
    )
    return list(cursor)


def get_trade_market_item_price(
    item_name: str,
    shiny: bool = False,
    tier: Optional[int] = None
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
        {'item_type': {'$in': ['GearItem', 'IngredientItem']}},
        {'item_type': 'MaterialItem', 'tier': tier}
    ]}

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

            'total_count': '$identifiedCount',
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

    cursor = get_collection(ColEnum.MARKET).aggregate(pipeline)
    try:
        stats = cursor.next()
    except StopIteration:
        return {}

    return stats


def get_price_history(
        item_name: str,
        shiny: bool = False,
        days: int = 14,
        tier: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve the price history of an item over the past `days` days.
    """
    shiny_stat = '$ne' if shiny else '$eq'
    query_filter: Dict[str, Any] = {'name': item_name, 'shiny_stat': {shiny_stat: None}, '$or': [
        {'item_type': {'$in': ['GearItem', 'IngredientItem']}},
        {'item_type': 'MaterialItem', 'tier': tier}
    ]}

    start_date = datetime.now(timezone.utc) - timedelta(days=days + 8)
    query_filter['date'] = {'$gte': start_date}

    cursor = get_collection(ColEnum.MARKET_ARCHIVE).find(
        filter=query_filter,
        sort=[('date', 1)],
        projection={'_id': 0}
    )
    
    return list(cursor)


def get_historic_average(item_name, shiny=False, tier=None, days=7):
    shiny_op = '$ne' if shiny else '$eq'
    query = {
      'name': item_name,
      'shiny_stat': {shiny_op: None},
      '$or': [
        {'item_type': {'$in': ['GearItem','IngredientItem']}},
        {'item_type': 'MaterialItem', 'tier': tier}
      ]
    }

    pipeline = [
      {'$match': query},
      {'$sort':  {'date': -1}},
      {'$limit': days},
      {'$group': {
         '_id': None,
         'name':        {'$first': '$name'},
         'tier':        {'$first': '$tier'},
         'document_count': {'$sum': 1},

         # average over the last N docs
         'lowest_price':  {'$avg': '$lowest_price'},
         'highest_price': {'$avg': '$highest_price'},
         'average_price': {'$avg': '$average_price'},

         'total_count':   {'$sum': '$total_count'},
         'avg_mid80':     {'$avg': '$average_mid_80_percent_price'},
         'unidentified_avg': {'$avg': '$unidentified_average_price'},
         'unidentified_mid80_avg': {'$avg': '$unidentified_average_mid_80_percent_price'},
         'unidentified_count': {'$sum': '$unidentified_count'}
      }},
      {'$project': {
         '_id': 0,
         'name': 1, 'tier': 1, 'document_count': 1,
         'lowest_price': {'$round': ['$lowest_price', 2]},
         'highest_price':{'$round': ['$highest_price',2]},
         'average_price':{'$round': ['$average_price',2]},
         'total_count': {'$toInt': '$total_count'},
         'average_mid_80_percent_price':     {'$round': ['$avg_mid80',2]},
         'unidentified_average_price':       {'$round': ['$unidentified_avg',2]},
         'unidentified_average_mid_80_percent_price': {'$round':['$unidentified_mid80_avg',2]},
         'unidentified_count':               {'$toInt': '$unidentified_count'}
      }}
    ]

    result = list(get_collection(ColEnum.MARKET_ARCHIVE)
                   .aggregate(pipeline, allowDiskUse=False))
    return result[0] if result else {}


def get_all_items_ranking(
        start_date: Optional[datetime] = None,
        end_date:   Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
        Retrieve a ranking of items based on archived price data,
        optionally filtered to the given [start_date, end_date] (inclusive).
        """
    pipeline: List[Dict[str, Any]] = []
    date_filter: Dict[str, Any] = {}

    if start_date:
        date_filter.setdefault('date', {})['$gte'] = start_date
    if end_date:
        exclusive_end = end_date + timedelta(days=1)
        date_filter.setdefault('date', {})['$lt']  = exclusive_end
    if start_date or end_date:
        pipeline.append({'$match': date_filter})

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
