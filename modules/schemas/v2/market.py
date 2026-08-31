"""Query models for the /api/v2/market endpoints."""
from typing import Literal, Optional

from pydantic import Field

from modules.models.sort_options import SortOption
from modules.schemas.v2.common import (
    DateRangeParams,
    PaginationParams,
    QueryModel,
    StrictBool,
)

ItemTypeLabel = Literal[
    'weapon', 'armour', 'accessory',
    'material', 'powder', 'amplifier', 'emerald_pouch',
]


class ListingsQuery(PaginationParams):
    item_name: Optional[str] = None
    item_type: Optional[ItemTypeLabel] = None
    subtype: Optional[str] = None
    rarity: Optional[str] = None
    tier: Optional[int] = Field(None, ge=1)
    shiny: Optional[StrictBool] = None
    unidentified: Optional[StrictBool] = None
    sort: SortOption = SortOption.TIMESTAMP_DESC


class PriceQuery(QueryModel):
    shiny: StrictBool = False
    tier: Optional[int] = Field(None, ge=1)


class HistoryQuery(PaginationParams, DateRangeParams):
    shiny: StrictBool = False
    tier: Optional[int] = Field(None, ge=1)


class HistoryLatestQuery(DateRangeParams):
    shiny: StrictBool = False
    tier: Optional[int] = Field(None, ge=1)


class RankingsQuery(PaginationParams, DateRangeParams):
    pass
