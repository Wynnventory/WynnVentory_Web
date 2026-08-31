"""/api/v2/market — trade market listings, prices, history, and rankings."""
from flask import Blueprint

market_v2_bp = Blueprint('market', __name__, url_prefix='/market')
