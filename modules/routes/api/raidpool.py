import logging
import time

from flask import request

from modules.auth import require_scope, mod_allowed
from modules.models.collection_types import Collection
from modules.routes.api.base_pool_blueprint import BasePoolBlueprint
from modules.services import raidpool_service
from modules.services.raidpool_service import save_gambits
from modules.utils.param_utils import api_response, handle_request_error

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
        return api_response({'message': 'No gambits provided'}, 400)

    try:
        save_gambits(data)
        return api_response({'message': 'Gambits received successfully'})
    except ValueError as ve:
        return handle_request_error(ve, error_msg="Validation error while processing gambits ", status_code=400)
    except Exception as e:
        return handle_request_error(e, error_msg="Error processing gambits")


@raidpool_bp.get('/raidpool/gambits/current')
@require_scope('read:raidpool')
def get_current_gambits():
    start_time = time.time()
    logger.info("GET /raidpool/gambits/current - Request started")
    
    try:
        service_start_time = time.time()
        logger.info("Calling raidpool_service.get_current_gambits")
        
        data = raidpool_service.get_current_gambits()
        
        service_duration = time.time() - service_start_time
        logger.info(f"raidpool_service.get_current_gambits completed in {service_duration:.3f}s")
        
        if data and isinstance(data, list):
            logger.info(f"Retrieved {len(data)} gambits")
        
        total_duration = time.time() - start_time
        logger.info(f"GET /raidpool/gambits/current completed in {total_duration:.3f}s")
        
        return api_response(data)
    except Exception as e:
        error_duration = time.time() - start_time
        logger.error(f"GET /raidpool/gambits/current failed after {error_duration:.3f}s: {str(e)}", exc_info=True)
        return handle_request_error(e)
