"""/api/v2/lootpools, /api/v2/raidpools, /api/v2/gambits — weekly pool data."""
from flask import Blueprint

lootpools_v2_bp = Blueprint('lootpools', __name__, url_prefix='/lootpools')
raidpools_v2_bp = Blueprint('raidpools', __name__, url_prefix='/raidpools')
gambits_v2_bp = Blueprint('gambits', __name__, url_prefix='/gambits')
