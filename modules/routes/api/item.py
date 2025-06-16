from flask import Blueprint, request
from pydantic import ValidationError

from modules.auth import public_endpoint
from modules.schemas.item_search import ItemSearchRequest
from modules.services import item_service
from modules.utils.param_utils import api_response, handle_request_error

item_bp = Blueprint('item', __name__, url_prefix='/api')

@item_bp.get('/item/<item_name>')
@public_endpoint
def get_item(item_name):
    data = item_service.fetch_item(item_name)

    if data:
        return api_response(data)

    return api_response({'message': 'Item not found'}, 404)

@item_bp.post('/items')
@public_endpoint
def search_items():
    try:
        req = ItemSearchRequest.model_validate(request.get_json() or {})
    except ValidationError as ve:
        return handle_request_error(ve, error_msg="Validation error while processing items", status_code=400)

    try:
        result = item_service.search_items(req)
        return api_response(result)
    except Exception as e:
        return handle_request_error(e)
