"""/api/v2/items — Wynncraft item database proxy."""
from flask import Blueprint

items_v2_bp = Blueprint('items', __name__, url_prefix='/items')
