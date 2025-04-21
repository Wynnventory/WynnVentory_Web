from modules.routes.api.base_pool_blueprint import BasePoolBlueprint
from modules.services.lootpool_service import LootpoolService

# Create a lootpool blueprint using the base class
pool_blueprint = BasePoolBlueprint('lootpool', LootpoolService())
lootpool_bp = pool_blueprint.blueprint
