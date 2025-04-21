from flask import Blueprint, request, jsonify

from modules.auth import require_scope
from modules.services.lootpool_service import LootpoolService

# Blueprint for lootpool API endpoints
lootpool_bp = Blueprint('lootpool', __name__, url_prefix='/api')
service = LootpoolService()

@lootpool_bp.post('/lootpool/items')
@require_scope('write:lootpool')
def save_lootpool_items():
    """
    POST /api/lootpool/items
    Save one or more lootpool payloads.
    """
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No items provided'}), 400

    try:
        service.save(data)
        return jsonify({'message': 'Items received successfully'}), 200
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception:
        return jsonify({'error': 'Internal server error'}), 500

@lootpool_bp.get('/lootpool/items')
@require_scope('read:lootpool')
def get_lootpool_items():
    """
    GET /api/lootpool/items
    Retrieve the processed lootpool items for the current week.
    """
    try:
        items = service.get_current_lootpool()
        return jsonify(items), 200
    except Exception:
        return jsonify({'error': 'Internal server error'}), 500

@lootpool_bp.get('/lootpool/raw')
@require_scope('read:lootpool')
def get_lootpool_raw():
    """
    GET /api/lootpool/raw
    Retrieve the raw lootpool documents for the current week.
    """
    try:
        raw = service.get_current_lootpool_raw()
        return jsonify(raw), 200
    except Exception:
        return jsonify({'error': 'Internal server error'}), 500