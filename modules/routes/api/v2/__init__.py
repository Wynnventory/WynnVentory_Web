"""The /api/v2 surface: standardized, versioned, key-only REST API.

Conventions (envelope, errors, naming, dates) are documented in
docs/api-v2-conventions.md. Routes reuse the existing service/repository
layer; all response-shape normalization happens in v2 serializers.
"""
from flask import Blueprint

from modules.auth import record_api_usage
from modules.routes.api.v2.auth import require_api_key_v2
from modules.routes.api.v2.responses import envelope
from modules.routes.api.v2.validation import validate
from modules.schemas.v2.common import EmptyQuery


def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = (
        'Authorization, X-API-Key, Content-Type')
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Max-Age'] = '86400'
    return response


def build_v2_blueprint():
    bp = Blueprint('api_v2', __name__, url_prefix='/api/v2')

    # Nested blueprints inherit these hooks.
    bp.before_request(require_api_key_v2)
    bp.after_request(record_api_usage)
    bp.after_request(add_cors_headers)

    @bp.get('/status')
    @validate(query=EmptyQuery)
    def status():
        return envelope({'status': 'ok', 'version': 'v2'})

    from modules.routes.api.v2.market import market_v2_bp
    bp.register_blueprint(market_v2_bp)

    from modules.routes.api.v2.items import items_v2_bp
    bp.register_blueprint(items_v2_bp)

    from modules.routes.api.v2.aspects import aspects_v2_bp
    bp.register_blueprint(aspects_v2_bp)

    from modules.routes.api.v2.pools import lootpools_v2_bp, raidpools_v2_bp, gambits_v2_bp
    bp.register_blueprint(lootpools_v2_bp)
    bp.register_blueprint(raidpools_v2_bp)
    bp.register_blueprint(gambits_v2_bp)

    return bp
