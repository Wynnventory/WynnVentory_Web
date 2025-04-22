from modules.models.collection_types import Collection
from modules.routes.api.base_pool_blueprint import BasePoolBlueprint

# Create a raidpool blueprint using the base class
pool_blueprint = BasePoolBlueprint('raidpool', Collection.RAID)
raidpool_bp = pool_blueprint.blueprint
