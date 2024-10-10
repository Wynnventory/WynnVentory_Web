from flask import Flask, redirect, url_for, request

ALLOWED_IPS = ["127.0.0.1",
               "83.76.209.66", # Pfister PC
               "178.197.215.137", # Tim Handy
               "85.2.46.237", # Tim PC
               "178.197.211.252", # Pfister Handy
               "213.55.241.4" # Säm PC
               ]


def is_allowed_ip():
    """Returns True if the user's IP is in the allowed list."""
    if request.headers.getlist("X-Forwarded-For"):
        user_ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        user_ip = request.remote_addr  # Fallback to remote address

    return user_ip in ALLOWED_IPS


def create_app():
    app = Flask(__name__,
                static_url_path='',
                static_folder='../templates/static',
                template_folder='../templates')

    # ROUTES
    from modules.routes.web import web_bp
    from modules.routes.api import api_bp
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)

    # 404 Error
    @app.errorhandler(404)
    def page_not_found(e):
        return redirect(url_for('web.index'), 404)

    @app.context_processor
    def inject_ip_check():
        """Injects whether the current user's IP is allowed into all templates."""
        show_price_history = is_allowed_ip()  # Perform IP check
        return dict(show_price_history=show_price_history)
    return app
