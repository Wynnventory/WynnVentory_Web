from flask import Blueprint, request, jsonify

from modules.auth import require_scope
from modules.services.market_service import MarketService, save_items

market_bp = Blueprint('market', __name__, url_prefix='/api')
service = MarketService()


@market_bp.post('/trademarket/items')
@require_scope('write:market')
def save_trade_market_items():
    """
    POST /api/trademarket/items
    Save one or more market items.
    """
    data = request.get_json()
    if not data or (isinstance(data, list) and len(data) == 0):
        return jsonify({'message': 'No items provided'}), 400

    try:
        save_items(data)
        return jsonify({'message': 'Items received successfully'}), 200
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception:
        return jsonify({'error': 'Internal server error'}), 500


@market_bp.get('/trademarket/item/<item_name>')
def get_market_item_info(item_name):
    """
    GET /api/trademarket/item/<item_name>
    Retrieve market item info by name.
    """
    if not item_name:
        return jsonify({'message': 'No item name provided'}), 400
    try:
        result = service.get_item(item_name)
        return jsonify(result), 200
    except Exception:
        return jsonify({'error': 'Internal server error'}), 500


@market_bp.get('/trademarket/item/<item_name>/price')
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
        result = service.get_price(item_name, shiny, tier)
        return jsonify(result), 200
    except Exception:
        return jsonify({'error': 'Internal server error'}), 500


@market_bp.get('/trademarket/history/<item_name>')
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
        result = service.get_history(item_name, shiny, days, tier)
        return jsonify(result), 200
    except Exception:
        return jsonify({'error': 'Internal server error'}), 500


@market_bp.get('/trademarket/history/<item_name>/latest')
def get_latest_market_history(item_name):
    """
    GET /api/trademarket/history/<item_name>/latest
    Retrieve latest aggregated price history for an item.
    """
    if not item_name:
        return jsonify({'message': 'No item name provided'}), 400
    shiny = request.args.get('shiny', 'false').lower() == 'true'
    tier_param = request.args.get('tier')
    tier = int(tier_param) if tier_param is not None else None

    try:
        result = service.get_latest_history(item_name, shiny, tier)
        return jsonify(result), 200
    except Exception:
        return jsonify({'error': 'Internal server error'}), 500


@market_bp.get('/trademarket/ranking')
def get_all_items_ranking():
    """
    GET /api/trademarket/ranking
    Retrieve a ranking of items by average price.
    """
    try:
        ranking = service.get_ranking()
        return jsonify(ranking), 200
    except Exception:
        return jsonify({'error': 'Internal server error'}), 500
