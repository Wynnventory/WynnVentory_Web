"""/api/v2/market — trade market listings, prices, history, and rankings."""
from flask import Blueprint

from modules.routes.api.v2.auth import require_scope_v2
from modules.routes.api.v2.errors import ApiError
from modules.routes.api.v2.responses import envelope, paginated
from modules.routes.api.v2.serializers.common import (
    item_type_to_storage,
    subtype_to_storage,
)
from modules.routes.api.v2.serializers.market import (
    serialize_listing,
    serialize_price_stats,
    serialize_ranking_entry,
)
from modules.routes.api.v2.validation import validate
from modules.schemas.v2.market import (
    HistoryLatestQuery,
    HistoryQuery,
    ListingsQuery,
    PriceQuery,
    RankingsQuery,
)
from modules.services.market_service import (
    get_history,
    get_historic_item_price,
    get_item_listings,
    get_price,
    get_ranking,
)

market_v2_bp = Blueprint('market', __name__, url_prefix='/market')


def _slice_page(items, page, page_size):
    start = (page - 1) * page_size
    return items[start:start + page_size]


@market_v2_bp.get('/listings')
@require_scope_v2('read:market')
@validate(query=ListingsQuery)
def listings(query: ListingsQuery):
    result = get_item_listings(
        item_name=query.item_name,
        shiny=query.shiny,
        unidentified=query.unidentified,
        rarity=query.rarity,
        tier=query.tier,
        item_type=item_type_to_storage(query.item_type),
        sub_type=subtype_to_storage(query.subtype),
        sort_option=query.sort,
        page=query.page,
        page_size=query.page_size,
    )
    return paginated(
        [serialize_listing(doc) for doc in result['items']],
        page=query.page,
        page_size=query.page_size,
        total_items=result['total'],
    )


@market_v2_bp.get('/items/<item_name>/price')
@require_scope_v2('read:market')
@validate(query=PriceQuery)
def item_price(item_name, query: PriceQuery):
    stats = get_price(item_name, query.shiny, query.tier)
    if not stats:
        raise ApiError('not_found', f"No price data for item '{item_name}'", 404)
    return envelope(serialize_price_stats(stats))


@market_v2_bp.get('/items/<item_name>/history')
@require_scope_v2('read:market')
@validate(query=HistoryQuery)
def item_history(item_name, query: HistoryQuery):
    points = get_history(
        item_name=item_name,
        shiny=query.shiny,
        tier=query.tier,
        start_date=query.start_date,
        end_date=query.end_date,
    )
    page_points = _slice_page(points, query.page, query.page_size)
    return paginated(
        [serialize_price_stats(point) for point in page_points],
        page=query.page,
        page_size=query.page_size,
        total_items=len(points),
    )


@market_v2_bp.get('/items/<item_name>/history/latest')
@require_scope_v2('read:market_archive')
@validate(query=HistoryLatestQuery)
def item_history_latest(item_name, query: HistoryLatestQuery):
    stats = get_historic_item_price(
        item_name=item_name,
        shiny=query.shiny,
        tier=query.tier,
        start_date=query.start_date,
        end_date=query.end_date,
    )
    if not stats:
        raise ApiError('not_found',
                       f"No archived price data for item '{item_name}'", 404)
    return envelope(serialize_price_stats(stats))


@market_v2_bp.get('/rankings')
@require_scope_v2('read:market')
@validate(query=RankingsQuery)
def rankings(query: RankingsQuery):
    ranked = get_ranking(start_date=query.start_date, end_date=query.end_date)
    page_rows = _slice_page(ranked, query.page, query.page_size)
    return paginated(
        [serialize_ranking_entry(row) for row in page_rows],
        page=query.page,
        page_size=query.page_size,
        total_items=len(ranked),
    )
