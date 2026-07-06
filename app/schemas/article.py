from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ArticleBase(BaseModel):
    parent_id: int
    type: str = Field("story", max_length=30)
    title_en: str = Field("", max_length=255)
    title_zh: str = Field("", max_length=255)
    content_en: str = ""
    content_zh: str = ""
    audio_src: str = Field("", max_length=512)
    lrc_position: Optional[list] = None
    question: Optional[Any] = None
    name_list: Optional[list] = None
    quote: Optional[Any] = None
    model: str = Field("deepseek-chat", max_length=100)
    input: dict[str, Any] = {}
    gen_type: Optional[str] = Field(None, max_length=20)
    gen_input: Optional[dict[str, Any]] = None
    ai_response: Optional[dict[str, Any]] = None


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    parent_id: Optional[int] = None
    type: Optional[str] = Field(None, max_length=30)
    title_en: Optional[str] = Field(None, max_length=255)
    title_zh: Optional[str] = Field(None, max_length=255)
    content_en: Optional[str] = None
    content_zh: Optional[str] = None
    audio_src: Optional[str] = Field(None, max_length=512)
    lrc_position: Optional[list] = None
    question: Optional[Any] = None
    name_list: Optional[list] = None
    quote: Optional[Any] = None
    model: Optional[str] = Field(None, max_length=100)
    input: Optional[dict[str, Any]] = None
    gen_type: Optional[str] = Field(None, max_length=20)
    gen_input: Optional[dict[str, Any]] = None
    ai_response: Optional[dict[str, Any]] = None


class ArticleOut(ArticleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ArticleBookBase(BaseModel):
    name: str = Field(..., max_length=120)
    parent_id: Optional[int] = None
    type: int = 0


class ArticleBookCreate(ArticleBookBase):
    pass


class ArticleBookUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=120)
    parent_id: Optional[int] = None
    type: Optional[int] = None


class ArticleBookOut(ArticleBookBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ArticleBookTreeNode(ArticleBookOut):
    children: list["ArticleBookTreeNode"] = []


class ArticleBatchUpdate(BaseModel):
    book_id: int
    type: Optional[str] = Field(None, max_length=30)
    audio_prefix: Optional[str] = Field(None, max_length=200)
    audio_find: Optional[str] = Field(None, max_length=500)
    audio_replace: Optional[str] = Field(None, max_length=500)


class ArticleGenerateRequest(BaseModel):
    book_id: int
    gen_type: str = Field(..., pattern=r"^(topic|words)$")
    topic: Optional[str] = Field(None, max_length=200)
    words: Optional[list[str]] = None
    difficulty: str = Field("medium", pattern=r"^(easy|medium|hard)$")
    word_count: Optional[int] = Field(None, ge=50, le=5000)


class WordGenerateRequest(BaseModel):
    book_id: int
    word: str = Field(..., min_length=1, max_length=120)
