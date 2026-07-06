from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WordBookBase(BaseModel):
    name: str = Field(..., max_length=120)
    parent_id: Optional[int] = None
    type: int = 0


class WordBookCreate(WordBookBase):
    pass


class WordBookUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=120)
    parent_id: Optional[int] = None
    type: Optional[int] = None


class WordBookOut(WordBookBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WordBookTreeNode(WordBookOut):
    children: list["WordBookTreeNode"] = []
