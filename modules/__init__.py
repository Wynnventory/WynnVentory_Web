from flask import Flask, redirect, url_for

from modules.db import get_client


def create_app():
    app = Flask(__name__,
                static_url_path='',
                static_folder='modules/routes/web/static',
                template_folder='modules/routes/web/templates')

    # ROUTES
    from modules.routes.web.web import web_bp
    from modules.routes.api.item import item_bp
    from modules.routes.api.aspect import aspect_bp
    from modules.routes.api.lootpool import lootpool_bp
    from modules.routes.api.raidpool import raidpool_bp
    from modules.routes.api.market import market_bp
    app.register_blueprint(web_bp)
    app.register_blueprint(item_bp)
    app.register_blueprint(aspect_bp)
    app.register_blueprint(lootpool_bp)
    app.register_blueprint(raidpool_bp)
    app.register_blueprint(market_bp)

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