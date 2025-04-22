from modules.models.collection_types import Collection
from modules.routes.api.base_pool_blueprint import BasePoolBlueprint

# Create a lootpool blueprint using the base class
pool_blueprint = BasePoolBlueprint('lootpool', Collection.LOOT)
lootpool_bp = pool_blueprint.blueprint
