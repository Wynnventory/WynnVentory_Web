"""/api/v2/items — Wynncraft item database proxy.

Any valid API key may call these routes (the v1 equivalents are public, so
existing keys carry no item-specific scope). Responses proxy the processed
Wynncraft item shape and are documented as free-form objects.
"""
from flask import Blueprint

from modules.routes.api.v2.errors import ApiError
from modules.routes.api.v2.responses import envelope
from modules.routes.api.v2.validation import validate
from modules.schemas.v2.items import ItemBatchBody
from modules.services.item_service import fetch_item

items_v2_bp = Blueprint('items', __name__, url_prefix='/items')


def _lookup(name):
    try:
        return fetch_item(name)
    except ValueError:
        # The Wynncraft API knows the item but this service cannot process
        # its type; from the caller's perspective the resource is unavailable.
        return None


@items_v2_bp.get('/<item_name>')
def get_item(item_name):
    item = _lookup(item_name)
    if not item:
        raise ApiError('not_found', f"Item '{item_name}' not found", 404)
    return envelope(item)


@items_v2_bp.post('/batch')
@validate(body=ItemBatchBody)
def get_items_batch(body: ItemBatchBody):
    # A read modeled as POST purely to carry the name list; the result maps
    # each requested name to its item object, or null when not found.
    return envelope({name: _lookup(name) for name in body.item_names})
