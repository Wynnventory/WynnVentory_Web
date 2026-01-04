import math
from datetime import datetime, timezone
from typing import Any

from flask import Flask, redirect, url_for

from modules.auth import require_api_key, record_api_usage
from modules.config import Config

UTC = timezone.utc

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
    def format_last_updated(value: Any) -> str:
        now = datetime.now(UTC)

        # 1) If it's already a datetime, use it (but reject naive)
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return "Invalid timestamp"  # or raise, but templates shouldn't 500
            ts = value.astimezone(UTC).replace(microsecond=0)

        # 2) Otherwise require ISO-8601 with timezone (Z or ±HH:MM)
        elif isinstance(value, str):
            s = value.strip()

            # Require timezone info in the string
            has_tz = s.endswith("Z") or ("+" in s) or ("-" in s[10:])  # offset after date part
            if not has_tz:
                return "Invalid timestamp"

            # Normalize Z -> +00:00
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"

            # Drop fractional seconds (we only care to seconds)
            if "." in s:
                before_dot, after_dot = s.split(".", 1)
                tz_part = ""
                if "+" in after_dot:
                    tz_part = "+" + after_dot.split("+", 1)[1]
                elif "-" in after_dot and ":" in after_dot[after_dot.rfind("-"):]:
                    tz_part = after_dot[after_dot.rfind("-"):]
                s = before_dot + tz_part

            try:
                ts = datetime.fromisoformat(s)
            except ValueError:
                return "Invalid timestamp"

            if ts.tzinfo is None:
                return "Invalid timestamp"
            ts = ts.astimezone(UTC).replace(microsecond=0)

        else:
            return "Invalid timestamp"

        # Compute human-readable delta
        diff_seconds = int((now - ts).total_seconds())
        if diff_seconds < 0:
            diff_seconds = 0

        diff_minutes = diff_seconds // 60
        if diff_minutes < 60:
            return f"{diff_minutes} minute{'s' if diff_minutes != 1 else ''}"

        diff_hours = diff_minutes // 60
        if diff_hours < 24:
            return f"{diff_hours} hour{'s' if diff_hours != 1 else ''}"

        diff_days = diff_hours // 24
        return f"{diff_days} day{'s' if diff_days != 1 else ''}"

    @app.template_filter('to_roman')
    def to_roman_numeral(num):
        if type(num) is not int:
            return num

        lookup = [
            (1000, 'M'),
            (900, 'CM'),
            (500, 'D'),
            (400, 'CD'),
            (100, 'C'),
            (90, 'XC'),
            (50, 'L'),
            (40, 'XL'),
            (10, 'X'),
            (9, 'IX'),
            (5, 'V'),
            (4, 'IV'),
            (1, 'I'),
        ]

        res = ''
        for (n, roman) in lookup:
            (d, num) = divmod(num, n)
            res += roman * d
        return res

    return app
