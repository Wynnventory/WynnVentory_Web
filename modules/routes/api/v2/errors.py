"""Error shape and error handlers for the /api/v2 surface.

Every v2 error body is {"error": {"code", "message", "details?"}} with a fixed
code vocabulary; see docs/api-v2-conventions.md.
"""
import logging

from flask import request
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)

_AUTH_CODES = ('missing_api_key', 'invalid_api_key')


class ApiError(Exception):
    """Raise anywhere inside a v2 request to produce a standard error response."""

    def __init__(self, code, message, status, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details


def error_response(code, message, status, details=None):
    from modules.routes.api.v2 import add_cors_headers
    from modules.routes.api.v2.responses import v2_json

    body = {'error': {'code': code, 'message': message}}
    if details is not None:
        body['error']['details'] = details

    response = v2_json(body, status)
    if code in _AUTH_CODES:
        response.headers['WWW-Authenticate'] = 'Api-Key'
    # Unmatched-path errors (404/405) never reach the blueprint's after_request
    # hook, so CORS headers are applied here as well.
    return add_cors_headers(response)


def _is_v2_request():
    return request.path.startswith('/api/v2')


def register_error_handlers(app):
    """Attach the v2 error handlers to the app. v1 and web behavior unchanged."""

    @app.errorhandler(ApiError)
    def handle_api_error(error):
        # Only v2 code raises ApiError, so this handler is safe app-wide.
        return error_response(error.code, error.message, error.status,
                              error.details)

    @app.errorhandler(Exception)
    def handle_unexpected(error):
        if isinstance(error, HTTPException):
            # 404 has its own (path-aware) handler; remaining HTTP errors such
            # as 405 get the v2 JSON shape only on v2 paths.
            if _is_v2_request():
                code = ('method_not_allowed' if error.code == 405
                        else 'not_found' if error.code == 404
                        else 'internal_error' if error.code >= 500
                        else 'validation_error')
                return error_response(code, error.description, error.code)
            return error
        if _is_v2_request():
            logger.error('Unhandled error on %s %s', request.method,
                         request.path, exc_info=True)
            return error_response('internal_error', 'Internal server error', 500)
        raise error
