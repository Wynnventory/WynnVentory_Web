from flask import Flask


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
    return app