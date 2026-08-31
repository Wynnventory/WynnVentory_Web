"""Request validation for the /api/v2 surface.

@validate parses request.args and/or the JSON body into Pydantic models and
injects them into the view as `query=` / `body=` keyword arguments. Any
validation failure becomes a structured 400 (see docs/api-v2-conventions.md).
"""
from functools import wraps

from flask import request
from pydantic import ValidationError

from modules.routes.api.v2.errors import ApiError


def _details(exc: ValidationError, location: str):
    return [
        {
            'field': '.'.join(str(part) for part in err['loc']) or '(root)',
            'location': location,
            'message': err['msg'],
        }
        for err in exc.errors()
    ]


def validate(query=None, body=None):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if query is not None:
                try:
                    kwargs['query'] = query.model_validate(request.args.to_dict())
                except ValidationError as exc:
                    raise ApiError('validation_error', 'Invalid query parameters',
                                   400, _details(exc, 'query'))
            if body is not None:
                data = request.get_json(silent=True)
                if data is None:
                    raise ApiError('validation_error',
                                   'Request body must be valid JSON', 400)
                try:
                    kwargs['body'] = body.model_validate(data)
                except ValidationError as exc:
                    raise ApiError('validation_error', 'Invalid request body',
                                   400, _details(exc, 'body'))
            return f(*args, **kwargs)

        return wrapped

    return decorator
