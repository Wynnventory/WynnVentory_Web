"""/api/v2/aspects — Wynncraft class aspect proxy."""
from flask import Blueprint

aspects_v2_bp = Blueprint('aspects', __name__, url_prefix='/aspects')
