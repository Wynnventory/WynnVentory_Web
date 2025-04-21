from modules.routes.api.base_pool_blueprint import BasePoolBlueprint
from modules.services.raidpool_service import RaidpoolService

# Create a raidpool blueprint using the base class
pool_blueprint = BasePoolBlueprint('raidpool', RaidpoolService())
raidpool_bp = pool_blueprint.blueprint
