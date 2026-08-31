"""Body models for the /api/v2/items endpoints."""
from typing import List

from pydantic import Field

from modules.schemas.v2.common import BodyModel


class ItemBatchBody(BodyModel):
    item_names: List[str] = Field(min_length=1, max_length=100)
