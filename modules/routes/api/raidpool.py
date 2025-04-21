from flask import Blueprint, request, jsonify

from modules.auth import require_scope
from modules.services.raidpool_service import RaidpoolService

raidpool_bp = Blueprint('raidpool', __name__, url_prefix='/api')
service = RaidpoolService()

@raidpool_bp.post('/raidpool/items')
@require_scope('write:raidpool')
def save_raidpool_items():
    """
    POST /api/raidpool/items
    Save one or more raidpool payloads.
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

@raidpool_bp.get('/raidpool/items')
@require_scope('read:raidpool')
def get_raidpool_items():
    """
    GET /api/raidpool/items
    Retrieve the processed raidpool items for the current week.
    """
    try:
        items = service.get_current_lootpool()
        return jsonify(items), 200
    except Exception:
        return jsonify({'error': 'Internal server error'}), 500

@raidpool_bp.get('/raidpool/raw')
@require_scope('read:raidpool')
def get_raidpool_raw():
    """
    GET /api/raidpool
    Retrieve the raw raidpool documents for the current week.
    """
    try:
        raw = service.get_current_lootpool_raw()
        return jsonify(raw), 200
    except Exception:
        return jsonify({'error': 'Internal server error'}), 500
