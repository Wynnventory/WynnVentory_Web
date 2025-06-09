import logging

from flask import request, jsonify

from modules.auth import require_scope, mod_allowed
from modules.models.collection_types import Collection
from modules.routes.api.base_pool_blueprint import BasePoolBlueprint
from modules.services import raidpool_service
from modules.services.raidpool_service import save_gambits

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s"
)

logger = logging.getLogger(__name__)

# Create a raidpool blueprint using the base class
pool_blueprint = BasePoolBlueprint('raidpool', Collection.RAID)
raidpool_bp = pool_blueprint.blueprint


@raidpool_bp.post('/raidpool/gambits')
@require_scope('write:raidpool')
@mod_allowed
def save_gambit_items():
    """
    POST /api/trademarket/items
    Save one or more market items.
    """
    data = request.get_json()

    if not data or (isinstance(data, list) and len(data) == 0):
        logger.warning("No gambits provided in request")
        return jsonify({'message': 'No gambits provided'}), 400

    try:
        save_gambits(data)
        return jsonify({'message': 'Gambits received successfully'}), 200
    except ValueError as ve:
        error_msg = str(ve)
        logger.warning(f"Validation error: {error_msg}")
        return jsonify({'error': error_msg}), 400
    except Exception as e:
        logger.error(f"Error processing gambits: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

@raidpool_bp.get('/raidpool/gambits/current')
@require_scope('read:raidpool')
def get_current_gambits():
    return jsonify(raidpool_service.get_current_gambits())