"""Query models for the /api/v2 pool endpoints."""
from pydantic import Field

from modules.schemas.v2.common import QueryModel


class PoolsListQuery(QueryModel):
    # Each pool is a full week of data, so the page size cap is small.
    page: int = Field(1, ge=1)
    page_size: int = Field(5, ge=1, le=8)
