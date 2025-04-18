from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from modules.schemas.item_search import ItemSearchRequest
from modules.services.item_service import ItemService

item_bp = Blueprint('item', __name__, url_prefix='/api')
service = ItemService()

@item_bp.get('/item/<item_name>')
def get_item(item_name):
    return jsonify(service.fetch_item(item_name))

@item_bp.post('/items')
def search_items():
    try:
        req = ItemSearchRequest.model_validate(request.get_json() or {})
    except ValidationError as e:
        return jsonify({"errors": e.errors()}), 400

    result = service.search_items(req)

    return jsonify(result), 200