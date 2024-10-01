from flask import Flask, redirect, url_for


def create_app():
    app = Flask(__name__, 
                static_url_path='',
                static_folder='../templates/static', 
                template_folder='../templates')
    
    # ROUTES
    from modules.routes.web import web_bp
    from modules.routes.api import api_bp
    
    # 404 Error
    @app.errorhandler(404)
    def page_not_found(e):
        return redirect(url_for('web.index'), 404)

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)
    return app