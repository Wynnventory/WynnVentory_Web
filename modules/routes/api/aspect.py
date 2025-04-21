from flask import Blueprint, request, jsonify

from modules.services import aspect_service

aspect_bp = Blueprint('aspect', __name__, url_prefix='/api')

@aspect_bp.get('/aspect/<class_name>/<aspect_name>')
def get_item(class_name, aspect_name):
    return jsonify(aspect_service.fetch_aspect(class_name, aspect_name))