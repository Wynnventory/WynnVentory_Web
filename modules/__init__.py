from flask import Flask


def create_app():
    app = Flask(__name__, static_folder='static', template_folder='../templates')
    
    # ROUTES
    from modules.routes.web import web_bp

    app.register_blueprint(web_bp)
    return app