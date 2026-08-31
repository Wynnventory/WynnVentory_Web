"""/api/v2/items — Wynncraft item database proxy.

Any valid API key may call these routes (the v1 equivalents are public, so
existing keys carry no item-specific scope). Responses proxy the processed
Wynncraft item shape and are documented as free-form objects.
"""
from concurrent.futures import ThreadPoolExecutor

from flask import Blueprint

from modules.routes.api.v2.errors import ApiError
from modules.routes.api.v2.responses import envelope
from modules.routes.api.v2.validation import validate
from modules.routes.api.wynncraft_api import UpstreamError
from modules.schemas.v2.common import EmptyQuery
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


def _upstream_unavailable(error):
    return ApiError('upstream_unavailable',
                    'The Wynncraft API is currently unavailable', 502)


@items_v2_bp.get('/<item_name>')
@validate(query=EmptyQuery)
def get_item(item_name, query: EmptyQuery):
    try:
        item = _lookup(item_name)
    except UpstreamError as error:
        raise _upstream_unavailable(error)
    if not item:
        raise ApiError('not_found', f"Item '{item_name}' not found", 404)
    return envelope(item)


@items_v2_bp.post('/batch')
@validate(body=ItemBatchBody)
def get_items_batch(body: ItemBatchBody):
    # A read modeled as POST purely to carry the name list; the result maps
    # each requested name to its item object, or null when not found.
    # Uncached lookups hit the upstream API, so fan them out.
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(_lookup, body.item_names))
    except UpstreamError as error:
        raise _upstream_unavailable(error)
    return envelope(dict(zip(body.item_names, results)))
