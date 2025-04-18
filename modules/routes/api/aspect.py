from flask import Blueprint, request, jsonify
from modules.services.aspect_service import AspectService

aspect_bp = Blueprint('aspect', __name__, url_prefix='/api')
service = AspectService()

@aspect_bp.get('/aspect/<class_name>/<aspect_name>')
def get_item(class_name, aspect_name):
    return jsonify(service.fetch_aspect(class_name, aspect_name))