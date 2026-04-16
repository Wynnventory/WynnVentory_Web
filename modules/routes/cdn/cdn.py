import os

from flask import Blueprint, send_from_directory

cdn_bp = Blueprint('cdn', __name__, url_prefix='/cdn')

ICONS_DIR = os.path.join(os.path.dirname(__file__), '../../routes/web/static/icons/wynn_icons')


@cdn_bp.after_request
def add_cdn_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Cache-Control'] = 'public, max-age=86400'
    return response


@cdn_bp.route('/icons/<path:filename>')
def serve_icon(filename):
    return send_from_directory(ICONS_DIR, filename)
