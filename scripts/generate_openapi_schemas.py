"""Dev helper: print the JSON Schemas of the v2 Pydantic request models.

Read-only — run it and paste/adapt the output into docs/openapi_v2.yaml when
a request model changes:

    python scripts/generate_openapi_schemas.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.schemas.v2.common import DateRangeParams, PaginationParams
from modules.schemas.v2.items import ItemBatchBody
from modules.schemas.v2.market import (
    HistoryLatestQuery,
    HistoryQuery,
    ListingsQuery,
    PriceQuery,
    RankingsQuery,
)
from modules.schemas.v2.pools import PoolsListQuery

MODELS = [
    PaginationParams, DateRangeParams,
    ListingsQuery, PriceQuery, HistoryQuery, HistoryLatestQuery, RankingsQuery,
    ItemBatchBody, PoolsListQuery,
]


def main():
    for model in MODELS:
        print(f'# --- {model.__name__} ---')
        print(json.dumps(model.model_json_schema(), indent=2))
        print()


if __name__ == '__main__':
    main()
