import logging

from flask import Blueprint, request, jsonify

from modules.auth import require_scope, public_endpoint
from modules.services.market_service import save_items, get_price, get_item, get_history, get_latest_history, \
    get_ranking

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s"
)

# Get module-specific logger
logger = logging.getLogger(__name__)

market_bp = Blueprint('market', __name__, url_prefix='/api')


@market_bp.post('/trademarket/items')
@require_scope('write:market')
def save_trade_market_items():
    """
    POST /api/trademarket/items
    Save one or more market items.
    """
    data = request.get_json()

    if not data or (isinstance(data, list) and len(data) == 0):
        logger.warning("No items provided in request")
        return jsonify({'message': 'No items provided'}), 400

    try:
        # Log the number of items and a sample of the data for debugging
        save_items(data)
        return jsonify({'message': 'Items received successfully'}), 200
    except ValueError as ve:
        error_msg = str(ve)
        logger.warning(f"Validation error: {error_msg}")
        return jsonify({'error': error_msg}), 400
    except Exception as e:
        logger.error(f"Error processing items: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@market_bp.get('/trademarket/item/<item_name>')
@require_scope('read:market')
def get_market_item_info(item_name):
    """
    GET /api/trademarket/item/<item_name>
    Retrieve market item info by name.
    """
    if not item_name:
        return jsonify({'message': 'No item name provided'}), 400
    try:
        result = get_item(item_name)
        return jsonify(result), 200
    except Exception:
        return jsonify({'error': 'Internal server error'}), 500


@market_bp.get('/trademarket/item/<item_name>/price')
@require_scope('read:market')
def get_market_item_price_info(item_name):
    """
    GET /api/trademarket/item/<item_name>/price
    Retrieve market item price statistics.
    """
    if not item_name:
        return jsonify({'message': 'No item name provided'}), 400
    shiny = request.args.get('shiny', 'false').lower() == 'true'
    tier_param = request.args.get('tier')
    tier = int(tier_param) if tier_param is not None else None

    try:
        result = get_price(item_name, shiny, tier)
        return jsonify(result), 200
    except Exception:
        return jsonify({'error': 'Internal server error'}), 500


@market_bp.get('/trademarket/history/<item_name>')
@public_endpoint
def get_market_history(item_name):
    """
    GET /api/trademarket/history/<item_name>
    Retrieve price history for an item over a number of days.
    """
    if not item_name:
        return jsonify({'message': 'No item name provided'}), 400
    try:
        days = int(request.args.get('days', 14))
    except ValueError:
        days = 14
    shiny = request.args.get('shiny', 'false').lower() == 'true'
    tier_param = request.args.get('tier')
    tier = int(tier_param) if tier_param is not None else None

    try:
        result = get_history(item_name, shiny, days, tier)
        return jsonify(result), 200
    except Exception:
        return jsonify({'error': 'Internal server error'}), 500


@market_bp.get('/trademarket/history/<item_name>/latest')
@require_scope('read:market_archive')
def get_latest_market_history(item_name):
    """
    GET /api/trademarket/history/<item_name>/latest
    Retrieve latest aggregated price history for an item.
    """
    if not item_name:
        return jsonify({'message': 'No item name provided'}), 400

    try:
        days = int(request.args.get('days', 7))
    except ValueError:
        days = 7

    shiny = request.args.get('shiny', 'false').lower() == 'true'
    tier_param = request.args.get('tier')
    tier = int(tier_param) if tier_param is not None else None

    try:
        result = get_latest_history(item_name=item_name, shiny=shiny, tier=tier, days=days)
        return jsonify(result), 200
    except Exception:
        return jsonify({'error': 'Internal server error'}), 500


@market_bp.get('/trademarket/ranking')
@public_endpoint
def get_all_items_ranking():
    """
    GET /api/trademarket/ranking
    Retrieve a ranking of items by average price.
    """
    try:
        ranking = get_ranking()
        return jsonify(ranking), 200
    except Exception:
        return jsonify({'error': 'Internal server error'}), 500
