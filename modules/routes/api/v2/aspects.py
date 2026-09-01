"""/api/v2/aspects — Wynncraft class aspect proxy.

Any valid API key may call this route (the v1 equivalent is public, so
existing keys carry no aspect-specific scope).
"""
from flask import Blueprint

from modules.routes.api.v2.errors import ApiError
from modules.routes.api.v2.responses import envelope
from modules.routes.api.v2.validation import validate
from modules.routes.api.wynncraft_api import UpstreamError
from modules.schemas.v2.common import EmptyQuery
from modules.services.aspect_service import fetch_aspect

aspects_v2_bp = Blueprint('aspects', __name__, url_prefix='/aspects')


@aspects_v2_bp.get('/<class_name>/<aspect_name>')
@validate(query=EmptyQuery)
def get_aspect(class_name, aspect_name):
    try:
        aspect = fetch_aspect(class_name, aspect_name)
    except UpstreamError:
        raise ApiError('upstream_unavailable',
                       'The Wynncraft API is currently unavailable', 502)
    if not aspect:
        raise ApiError(
            'not_found',
            f"Aspect '{aspect_name}' for class '{class_name}' not found", 404)
    return envelope(aspect)
