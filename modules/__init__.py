import math

from flask import Flask, redirect, url_for

from modules.auth import require_api_key, record_api_usage
from modules.config import Config


def create_app():
    app = Flask(__name__,
                static_url_path='',
                static_folder='modules/routes/web/static',
                template_folder='modules/routes/web/templates')

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

    app.logger.warning(
        "Successfully started in '%s' mode with min supported version '%s'",
        Config.ENVIRONMENT,
        Config.MIN_SUPPORTED_VERSION,
    )

    # 404 Error
    @app.errorhandler(404)
    def page_not_found(error):
        return redirect(url_for('web.index'))

    @app.template_filter('emerald_format')
    def emerald_format(emeralds):
        """
        Turns a raw emerald‐count (float or int) into the Wynncraft style:
          stx,le,eb,e
        """
        # ensure int
        rem = math.floor(emeralds)
        stx = rem // (64 ** 3)
        rem %= 64 ** 3

        le = rem // (64 ** 2)
        rem %= 64 ** 2

        eb = rem // 64
        rem %= 64

        # build result
        if stx > 0:
            # we want two‐decimal precision on the LE portion (le + eb/64 + rem/64²)
            dec = le + eb / 64 + rem / (64 ** 2)
            dec = round(dec, 2)
            # if dec is zero, omit the “Xle” part
            return f"{stx}stx{f' {dec}le' if dec else ''}".strip()
        else:
            parts = []
            if le:
                parts.append(f"{le}le")
            if eb:
                parts.append(f"{eb}eb")
            if rem:
                # show raw emeralds with two decimals
                parts.append(f"{rem:.2f}e")
            return " ".join(parts) or "0e"

    return app
