import math
from datetime import datetime, timezone

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
        Turns a raw emerald‐count into Wynncraft style,
        only showing decimals when needed.
        """
        rem = math.floor(emeralds)
        stx = rem // (64 ** 3)
        rem %= (64 ** 3)

        le = rem // (64 ** 2)
        rem %= (64 ** 2)

        eb = rem // 64
        rem %= 64

        if stx > 0:
            # compute total LE fraction
            dec = le + eb / 64 + rem / (64 ** 2)
            dec = round(dec, 2)
            if dec == 0:
                return f"{stx}stx"
            # drop trailing .0 or .00
            if dec.is_integer():
                dec_str = str(int(dec))
            else:
                # strip any trailing zeros, then a trailing dot
                dec_str = f"{dec:.2f}".rstrip('0').rstrip('.')
            return f"{stx}stx {dec_str}le"
        else:
            parts = []
            if le:
                parts.append(f"{le}le")
            if eb:
                parts.append(f"{eb}eb")
            if rem:
                parts.append(f"{rem}e")
            return " ".join(parts) or "0e"

    @app.template_filter("last_updated")
    def format_last_updated(timestamp_str: str) -> str:
        now = datetime.now(timezone.utc)

        ts = None
        # 1) Try ISO format first:
        try:
            ts = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f") \
                .replace(tzinfo=timezone.utc)
        except ValueError:
            # 2) Fall back to RFC‐style if ISO parse fails
            try:
                ts = datetime.strptime(timestamp_str, "%a, %d %b %Y %H:%M:%S %Z") \
                    .replace(tzinfo=timezone.utc)
            except ValueError:
                # If neither format matches, you could return a default or raise:
                return "Invalid timestamp"

        # Now ts is a timezone‐aware datetime
        minutes = (now - ts).total_seconds() // 60
        if minutes < 60:
            return f"{int(minutes)} minutes"
        hours = minutes // 60
        return f"{int(hours)} hour{'s' if hours > 1 else ''}"

    return app
