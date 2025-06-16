from flask import Blueprint, request

from modules.auth import require_scope, public_endpoint, mod_allowed
from modules.services.market_service import save_items, get_price, get_item_listings, get_history, \
    get_historic_item_price, \
    get_ranking
from modules.utils.param_utils import api_response, parse_boolean_param, parse_tier_param, parse_date_params
from modules.utils.param_utils import handle_request_error

market_bp = Blueprint('market', __name__, url_prefix='/api')


@market_bp.post('/trademarket/items')
@require_scope('write:market')
@mod_allowed
def save_trade_market_items():
    """
    POST /api/trademarket/items
    Save one or more market items.
    """
    data = request.get_json()

    if not data or (isinstance(data, list) and len(data) == 0):
        return api_response({'message': 'No items provided'}, 400)

    try:
        # Log the number of items and a sample of the data for debugging
        save_items(data)
        return api_response({'message': 'Items received successfully'})
    except ValueError as ve:
        return handle_request_error(ve, "Validation error while processing items", 400)
    except Exception as e:
        return handle_request_error(e, "Error processing items")


@market_bp.get('/trademarket/listings', defaults={'item_name': None})
@market_bp.get('/trademarket/listings/<item_name>')
@require_scope('read:market')
def get_market_item_info(item_name):
    """
    GET /api/trademarket/item/<item_name>
    Retrieve market item info by name.
    """
    rarity = request.args.get('rarity', None, type=str)
    page = max(1, request.args.get('page', 1, type=int))
    page_size = min(1000, request.args.get('page_size', 50, type=int))

    # Parse boolean parameters
    shiny = parse_boolean_param(request.args.get('shiny'))
    unidentified = parse_boolean_param(request.args.get('unidentified'))

    # Parse tier parameter
    tier = parse_tier_param(request.args.get('tier'))

    type_param = request.args.get('itemType')
    subtype_param = request.args.get('subType', type=str)
    sort_option = request.args.get('sort')

    try:
        result = get_item_listings(
            item_name=item_name,
            shiny=shiny,
            unidentified=unidentified,
            rarity=rarity,
            tier=tier,
            item_type=type_param,
            sub_type=subtype_param,
            sort_option=sort_option,
            page=page,
            page_size=page_size,
        )

        return api_response(result)
    except Exception as e:
        return handle_request_error(e)


@market_bp.get('/trademarket/item/<item_name>/price')
@require_scope('read:market')
@mod_allowed
def get_market_item_price_info(item_name):
    """
    GET /api/trademarket/item/<item_name>/price
    Retrieve market item price statistics.
    """
    if not item_name:
        return api_response({'message': 'No item name provided'}, 400)

    # Parse boolean parameter
    shiny = parse_boolean_param(request.args.get('shiny'))

    # Parse tier parameter
    tier = parse_tier_param(request.args.get('tier'))

    try:
        result = get_price(item_name, shiny, tier)
        return api_response(result)
    except Exception as e:
        return handle_request_error(e)


@market_bp.get('/trademarket/history/<item_name>')
@public_endpoint
def get_market_history(item_name):
    """
    GET /api/trademarket/history/<item_name>?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    Retrieve price history for an item over a date range (inclusive).
    If no dates are provided, returns the past 7 days.
    """
    if not item_name:
        return api_response({'message': 'No item name provided'}, 400)

    # Parse date parameters
    start_date, end_date, date_error = parse_date_params(
        request.args.get('start_date'),
        request.args.get('end_date')
    )

    if date_error:
        return api_response(date_error, 400)

    # Parse boolean parameter
    shiny = parse_boolean_param(request.args.get('shiny'))

    # Parse tier parameter
    tier = parse_tier_param(request.args.get('tier'))

    try:
        result = get_history(
            item_name=item_name,
            shiny=shiny,
            tier=tier,
            start_date=start_date,
            end_date=end_date
        )

        return api_response(result)
    except Exception as e:
        return handle_request_error(e)


@market_bp.get('/trademarket/history/<item_name>/price')
@market_bp.get('/trademarket/history/<item_name>/latest')  # required for mod versions before v1.1
@require_scope('read:market_archive')
@mod_allowed
def get_latest_market_history(item_name):
    """
    GET /api/trademarket/history/<item_name>/latest
    Retrieve latest aggregated price history for an item.
    """
    if not item_name:
        return api_response({'message': 'No item name provided'}, 400)

    # Parse date parameters
    start_date, end_date, date_error = parse_date_params(
        request.args.get('start_date'),
        request.args.get('end_date')
    )

    if date_error:
        return api_response(date_error, 400)

    # Parse boolean parameter
    shiny = parse_boolean_param(request.args.get('shiny'))

    # Parse tier parameter
    tier = parse_tier_param(request.args.get('tier'))

    try:
        result = get_historic_item_price(
            item_name=item_name,
            shiny=shiny,
            tier=tier,
            start_date=start_date,
            end_date=end_date
        )
        return api_response(result)
    except Exception as e:
        return handle_request_error(e)


@market_bp.get('/trademarket/ranking')
@public_endpoint
def get_all_items_ranking_endpoint():
    """
    GET /api/trademarket/ranking?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    Retrieve a ranking of items by average price, optionally restricted to a date range.
    """
    # Parse date parameters
    start_date, end_date, date_error = parse_date_params(
        request.args.get('start_date'),
        request.args.get('end_date')
    )

    if date_error:
        return api_response(date_error, 400)

    try:
        ranking = get_ranking(start_date=start_date, end_date=end_date)
        return api_response(ranking)
    except Exception as e:
        return handle_request_error(e)
