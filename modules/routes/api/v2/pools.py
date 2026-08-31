"""/api/v2/lootpools, /api/v2/raidpools, /api/v2/gambits — weekly pool data."""
from flask import Blueprint

from modules.models.collection_types import Collection
from modules.repositories.base_pool_repo import count_pool_weeks
from modules.routes.api.v2.auth import require_scope_v2
from modules.routes.api.v2.errors import ApiError
from modules.routes.api.v2.responses import envelope, paginated
from modules.routes.api.v2.serializers.pools import (
    serialize_processed_region,
    serialize_raw_pool,
)
from modules.routes.api.v2.validation import validate
from modules.schemas.v2.common import EmptyQuery
from modules.schemas.v2.pools import PoolsListQuery
from modules.services import base_pool_service, raidpool_service
from modules.utils.time_validation import get_lootpool_week, get_raidpool_week


def _validate_week(year, week):
    details = []
    if not 2020 <= year <= 2100:
        details.append({'field': 'year', 'location': 'path',
                        'message': 'must be between 2020 and 2100'})
    if not 1 <= week <= 53:
        details.append({'field': 'week', 'location': 'path',
                        'message': 'must be between 1 and 53'})
    if details:
        raise ApiError('validation_error', 'Invalid pool week', 400, details)


def _build_pool_blueprint(name, collection_type, scope, week_fn):
    bp = Blueprint(name, __name__, url_prefix=f'/{name}')

    def _pool_or_404(year, week):
        pool = base_pool_service.get_specific_pool(collection_type, year, week)
        if not pool:
            raise ApiError('not_found',
                           f'No {name} data for {year} week {week}', 404)
        return envelope(serialize_raw_pool(pool))

    @bp.get('')
    @require_scope_v2(scope)
    @validate(query=PoolsListQuery)
    def list_pools(query: PoolsListQuery):
        skip = (query.page - 1) * query.page_size
        result = base_pool_service.get_pools(
            collection_type=collection_type,
            page=query.page,
            page_size=query.page_size,
            skip=skip,
        )
        return paginated(
            [serialize_raw_pool(pool) for pool in result.get('pools', [])],
            page=query.page,
            page_size=query.page_size,
            total_items=count_pool_weeks(collection_type),
        )

    @bp.get('/current')
    @require_scope_v2(scope)
    @validate(query=EmptyQuery)
    def current_pool(query: EmptyQuery):
        year, week = week_fn()
        return _pool_or_404(year, week)

    @bp.get('/current/items')
    @require_scope_v2(scope)
    @validate(query=EmptyQuery)
    def current_pool_items(query: EmptyQuery):
        regions = base_pool_service.get_current_pools(collection_type)
        return envelope([serialize_processed_region(region)
                         for region in regions])

    @bp.get('/<int:year>/<int:week>')
    @require_scope_v2(scope)
    @validate(query=EmptyQuery)
    def specific_pool(year, week, query: EmptyQuery):
        _validate_week(year, week)
        return _pool_or_404(year, week)

    return bp


lootpools_v2_bp = _build_pool_blueprint(
    'lootpools', Collection.LOOT, 'read:lootpool', get_lootpool_week)
raidpools_v2_bp = _build_pool_blueprint(
    'raidpools', Collection.RAID, 'read:raidpool', get_raidpool_week)

gambits_v2_bp = Blueprint('gambits', __name__, url_prefix='/gambits')


@gambits_v2_bp.get('/current')
@require_scope_v2('read:raidpool')
@validate(query=EmptyQuery)
def current_gambits(query: EmptyQuery):
    data = raidpool_service.get_current_gambits()
    if not data:
        raise ApiError('not_found', 'No gambit data for the current day', 404)
    return envelope(data)
