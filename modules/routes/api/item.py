from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from modules.schemas.item_search import ItemSearchRequest
from modules.services import item_service

item_bp = Blueprint('item', __name__, url_prefix='/api')

@item_bp.get('/item/<item_name>')
def get_item(item_name):
    return jsonify(item_service.fetch_item(item_name))

@item_bp.post('/items')
def search_items():
    try:
        req = ItemSearchRequest.model_validate(request.get_json() or {})
    except ValidationError as e:
        return jsonify({"errors": e.errors()}), 400

    result = search_items(req)

    return jsonify(result), 200