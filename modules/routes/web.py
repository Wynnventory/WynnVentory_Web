from flask import Blueprint, render_template


web_bp = Blueprint('web', __name__)

@web_bp.route("/")
@web_bp.route("/index")
def index():
    return render_template("index.html")