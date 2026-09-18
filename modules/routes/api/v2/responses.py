"""Response builders for the /api/v2 surface.

v2 responses are built here instead of flask.jsonify so that datetimes are
serialized as ISO-8601 UTC ("2026-08-31T12:00:00Z") without touching the
app-wide JSON provider — v1 consumers (the website's strptime parsing and the
game mod) depend on Flask's default HTTP-date output.
"""
import json
import math
from datetime import date, datetime, timezone

from flask import Response


def _json_default(obj):
    if isinstance(obj, datetime):
        # Mongo may hand back naive datetimes; they are UTC by convention.
        if obj.tzinfo is None:
            obj = obj.replace(tzinfo=timezone.utc)
        return (obj.astimezone(timezone.utc)
                .replace(microsecond=0)
                .isoformat()
                .replace('+00:00', 'Z'))
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f'Object of type {type(obj).__name__} is not JSON serializable')


def v2_json(payload, status=200):
    """Serialize a payload with v2 conventions and return a Response."""
    return Response(
        json.dumps(payload, default=_json_default, separators=(',', ':')),
        status=status,
        mimetype='application/json',
    )


def envelope(data, status=200):
    """Standard v2 success envelope for single resources and non-paginated data."""
    return v2_json({'data': data}, status)


def paginated(items, page, page_size, total_items, status=200):
    """Standard v2 success envelope for paginated collections."""
    return v2_json({
        'data': items,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total_items': total_items,
            'total_pages': max(1, math.ceil(total_items / page_size)),
        },
    }, status)
