"""Shared Pydantic building blocks for /api/v2 request validation."""
from datetime import date, datetime, timezone
from typing import Annotated, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def _parse_strict_bool(value):
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ('true', '1'):
        return True
    if text in ('false', '0'):
        return False
    raise ValueError('must be one of: true, false, 1, 0')


# Boolean query parameter: only true/false/1/0 are accepted (case-insensitive).
StrictBool = Annotated[bool, BeforeValidator(_parse_strict_bool)]


def _parse_utc_date(value):
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime(value.year, value.month, value.day)
    else:
        try:
            parsed = datetime.fromisoformat(str(value))
        except ValueError:
            raise ValueError('must be an ISO-8601 date (YYYY-MM-DD)')
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


# Date query parameter: YYYY-MM-DD or full ISO-8601, normalized to aware UTC.
UtcDate = Annotated[datetime, BeforeValidator(_parse_utc_date)]


class QueryModel(BaseModel):
    """Base for query-string models: unknown parameters are a 400."""
    model_config = ConfigDict(extra='forbid')


class BodyModel(BaseModel):
    """Base for JSON body models: unknown fields are a 400."""
    model_config = ConfigDict(extra='forbid')


class PaginationParams(QueryModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=200)


class DateRangeParams(QueryModel):
    start_date: Optional[UtcDate] = None
    end_date: Optional[UtcDate] = None
