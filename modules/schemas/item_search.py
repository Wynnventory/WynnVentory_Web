from typing import List, Optional, Tuple

from pydantic import BaseModel, Field, conint


class ItemSearchRequest(BaseModel):
    query: Optional[str] = None
    type: List[str] = Field(default_factory=list)
    tier: List[int] = Field(default_factory=list)
    attackSpeed: List[int] = Field(default_factory=list)
    levelRange: Tuple[int, int] = (0, 110)
    professions: List[str] = Field(default_factory=list)
    identifications: List[str] = Field(default_factory=list)
    majorIds: List[str] = Field(default_factory=list)
    page: conint(ge=1) = 1
