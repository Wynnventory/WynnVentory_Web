import logging
from datetime import datetime, timezone

from flask import Blueprint, g, request

from modules.auth import require_scope, mod_allowed
from modules.models.collection_types import Collection
from modules.services import base_pool_service
from modules.utils.param_utils import api_response, handle_request_error
from modules.utils.time_validation import get_lootpool_week, get_raidpool_week, is_in_reset_window

logger = logging.getLogger(__name__)


class BasePoolBlueprint:
    """
    Base class for creating pool-related API blueprints (lootpool, raidpool).
    Provides common endpoint definitions and error handling.
    """

    def __init__(self, name: str, collection_type: Collection):
        """
        Initialize the blueprint with a name and service instance.

        Args:
            name (str): The name of the pool (e.g., 'lootpool', 'raidpool')
            service (Any): The service instance to use for operations
        """
        self.name = name
        self.collection_type = collection_type
        self.blueprint = Blueprint(name, __name__, url_prefix='/api')

        # Register the endpoints
        self._register_endpoints()

    def _register_endpoints(self):
        """Register all endpoints for this blueprint."""

        collection_type = self.collection_type

        @self.blueprint.post(f'/{self.name}/items')
        @require_scope(f'write:{self.name}')
        @mod_allowed
        def save_items():
            """
            POST /api/{name}/items
            Save one or more pool payloads.
            """
            data = request.get_json()
            if not data:
                return api_response({'message': 'No items provided'}, 400)

            _maybe_log_debug_payload(collection_type, data)

            try:
                base_pool_service.save(collection_type=collection_type, raw_data=data)
                return api_response({'message': 'Items received successfully'})
            except ValueError as ve:
                return handle_request_error(ve, error_msg="Validation error while processing items", status_code=400)
            except Exception as e:
                return handle_request_error(e)

        @self.blueprint.get(f'/{self.name}/items')
        @require_scope(f'read:{self.name}')
        def get_items():
            """
            GET /api/{name}/items
            Retrieve the processed pool items for the current week.
            """
            try:
                items = base_pool_service.get_current_pools(self.collection_type)
                return api_response(items)
            except Exception as e:
                return handle_request_error(e)

        @self.blueprint.get(f'/{self.name}/current')
        @require_scope(f'read:{self.name}')
        @mod_allowed
        def get_raw():
            """
            GET /api/{name}/current
            Retrieve the pools for the current week.
            """
            try:
                if self.collection_type == Collection.LOOT:
                    year, week = get_lootpool_week()
                    return get_specific_pool(year, week)
                elif self.collection_type == Collection.RAID:
                    year, week = get_raidpool_week()
                    return get_specific_pool(year, week)

                return api_response({'message': 'No data found'}, 404)
            except Exception as e:
                return handle_request_error(e)

        @self.blueprint.get(f'/{self.name}/all')
        @require_scope(f'read:{self.name}')
        def get_pools():
            """
            GET /api/{name}/all
            Retrieve all pools
            """
            page = max(1, request.args.get('page', 1, type=int))
            page_size = min(5, request.args.get('page_size', 5, type=int))  # cap at 5 weeks

            skip = (page - 1) * page_size

            try:
                raw = base_pool_service.get_pools(
                    collection_type=self.collection_type,
                    page=page,
                    page_size=page_size,
                    skip=skip
                )

                return api_response(raw)
            except Exception as e:
                return handle_request_error(e)

        @self.blueprint.get(f'/{self.name}/<int:year>/<int:week>')
        @require_scope(f'read:{self.name}')
        def get_specific_pool(year, week):
            """
            GET /api/{name}/year/week
            Retrieve a specific pool
            """
            try:
                raw = base_pool_service.get_specific_pool(self.collection_type, year, week)
                return api_response(raw)
            except Exception as e:
                return handle_request_error(e)


def _maybe_log_debug_payload(collection_type: Collection, data: dict) -> None:
    """Insert raw payload into debug collection when near a pool reset. Never raises."""
    if collection_type not in (Collection.LOOT, Collection.RAID):
        return
    try:
        if not is_in_reset_window(collection_type):
            return
        from modules.db import get_collection
        doc = {
            "received_at": datetime.now(timezone.utc),
            "pool_type": collection_type.value,
            "owner": getattr(g, "owner", None),
            "is_mod_key": getattr(g, "is_mod_key", None),
            "raw_body": request.get_data(as_text=True),
            "raw_payload": data,
        }
        get_collection(Collection.LOOT_DEBUG).insert_one(doc)
    except Exception:
        logger.exception("Failed to write debug payload log — continuing normally")
