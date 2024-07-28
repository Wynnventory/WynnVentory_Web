from flask import Blueprint, jsonify

from modules import wynn_api


api_bp = Blueprint('api', __name__)

@api_bp.route("/api/item/<item_name>")
def get_item_stats(item_name):
    item = wynn_api.quick_search_item(item_name)
    return jsonify(item)