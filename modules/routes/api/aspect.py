from flask import Blueprint

from modules.services import aspect_service
from modules.utils.param_utils import api_response, handle_request_error

aspect_bp = Blueprint('aspect', __name__, url_prefix='/api')


@aspect_bp.get('/aspect/<class_name>/<aspect_name>')
def get_item(class_name, aspect_name):
    try:
        data = aspect_service.fetch_aspect(class_name, aspect_name)
        return api_response(data)
    except Exception as e:
        return handle_request_error(e)
