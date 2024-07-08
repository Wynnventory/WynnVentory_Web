from flask import Blueprint, render_template


web_bp = Blueprint('web', __name__)

@web_bp.route("/")
@web_bp.route("/index")
def index():
    return render_template("index.html")

@web_bp.route("/items")
def items():
    return render_template("index.html")

@web_bp.route("/players")
def players():
    return render_template("index.html")