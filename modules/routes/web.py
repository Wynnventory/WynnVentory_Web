from flask import Blueprint, render_template
from modules import wynn_api


web_bp = Blueprint('web', __name__)

@web_bp.route("/")
@web_bp.route("/index")
def index():
    return render_template("index.html")

@web_bp.route("/items")
def items():
    items = wynn_api.get_item_database()
    return render_template("items.html", items=items)

@web_bp.route("/players")
def players():
    return render_template("index.html")