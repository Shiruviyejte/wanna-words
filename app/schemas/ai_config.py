from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AIConfigBase(BaseModel):
    group: Optional[str] = Field(None, max_length=20)
    base_url: Optional[str] = Field(None, max_length=255)
    api_key: Optional[str] = Field(None, max_length=255)
    model: str = Field("deepseek-chat", max_length=50)
    is_default_mode: bool = False


class AIConfigCreate(AIConfigBase):
    pass


class AIConfigUpdate(BaseModel):
    group: Optional[str] = Field(None, max_length=20)
    base_url: Optional[str] = Field(None, max_length=255)
    api_key: Optional[str] = Field(None, max_length=255)
    model: Optional[str] = Field(None, max_length=50)
    is_default_mode: Optional[bool] = None


class AIConfigOut(AIConfigBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
