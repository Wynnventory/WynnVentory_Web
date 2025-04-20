from flask import Flask, redirect, url_for
from decouple import config as env_config

from modules.auth import require_api_key, record_api_usage
from modules.config import Config
from modules.db import get_client


def create_app():
    app = Flask(__name__,
                static_url_path='',
                static_folder='modules/routes/web/static',
                template_folder='modules/routes/web/templates')

    Config.ENVIRONMENT = env_config("ENVIRONMENT")
    Config.MIN_SUPPORTED_VERSION = env_config("MIN_SUPPORTED_VERSION")

    # WEB ROUTES
    from modules.routes.web.web import web_bp
    app.register_blueprint(web_bp)

    # WEB ROUTES
    from modules.routes.api.item import item_bp
    from modules.routes.api.aspect import aspect_bp
    from modules.routes.api.lootpool import lootpool_bp
    from modules.routes.api.raidpool import raidpool_bp
    from modules.routes.api.market import market_bp

    for bp in (item_bp, aspect_bp, lootpool_bp, raidpool_bp, market_bp):
        bp.before_request(require_api_key)
        bp.after_request(record_api_usage)
        app.register_blueprint(bp)

    # Send a ping to confirm a successful connection
    try:
        get_client().admin.command('ping')
        print("Successfully connected to MongoDB!")
    except Exception as e:
        print("Could not connect to MongoDB!", e)

    # 404 Error
    @app.errorhandler(404)
    def page_not_found():
        return redirect(url_for('web.index'), 404)

    return app