from flask import Blueprint, request, jsonify
from typing import Callable, Any

from modules.auth import require_scope


class BasePoolBlueprint:
    """
    Base class for creating pool-related API blueprints (lootpool, raidpool).
    Provides common endpoint definitions and error handling.
    """

    def __init__(self, name: str, service: Any):
        """
        Initialize the blueprint with a name and service instance.
        
        Args:
            name (str): The name of the pool (e.g., 'lootpool', 'raidpool')
            service (Any): The service instance to use for operations
        """
        self.name = name
        self.service = service
        self.blueprint = Blueprint(name, __name__, url_prefix='/api')
        
        # Register the endpoints
        self._register_endpoints()
    
    def _register_endpoints(self):
        """Register all endpoints for this blueprint."""
        
        @self.blueprint.post(f'/{self.name}/items')
        @require_scope(f'write:{self.name}')
        def save_items():
            """
            POST /api/{name}/items
            Save one or more pool payloads.
            """
            data = request.get_json()
            if not data:
                return jsonify({'message': 'No items provided'}), 400
            
            try:
                self.service.save(data)
                return jsonify({'message': 'Items received successfully'}), 200
            except ValueError as ve:
                return jsonify({'error': str(ve)}), 400
            except Exception:
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.blueprint.get(f'/{self.name}/items')
        @require_scope(f'read:{self.name}')
        def get_items():
            """
            GET /api/{name}/items
            Retrieve the processed pool items for the current week.
            """
            try:
                items = self.service.get_current_lootpool()
                return jsonify(items), 200
            except Exception:
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.blueprint.get(f'/{self.name}/raw')
        @require_scope(f'read:{self.name}')
        def get_raw():
            """
            GET /api/{name}/raw
            Retrieve the raw pool documents for the current week.
            """
            try:
                raw = self.service.get_current_lootpool_raw()
                return jsonify(raw), 200
            except Exception:
                return jsonify({'error': 'Internal server error'}), 500