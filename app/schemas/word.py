from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class WordEntryBase(BaseModel):
    word: str = Field(..., max_length=120)
    phonetic0: Optional[str] = None
    phonetic1: Optional[str] = None
    synos: list[dict[str, Any]] = []
    etymology: list[dict[str, Any]] = []
    inflections: Optional[Any] = None
    e2e: Optional[Any] = None
    exams_src: Optional[Any] = None
    rel_words: Optional[dict[str, Any]] = None
    lang_type: str = "en"
    trans: list[dict[str, Any]] = []
    sentences: list[dict[str, Any]] = []
    phrases: list[dict[str, Any]] = []
    entry_type: str = "word"
    sequence: int = 1


class WordEntryCreate(WordEntryBase):
    book_id: int


class WordEntryUpdate(BaseModel):
    word: Optional[str] = Field(None, max_length=120)
    phonetic0: Optional[str] = None
    phonetic1: Optional[str] = None
    synos: Optional[list[dict[str, Any]]] = None
    etymology: Optional[list[dict[str, Any]]] = None
    inflections: Optional[Any] = None
    e2e: Optional[Any] = None
    exams_src: Optional[Any] = None
    rel_words: Optional[dict[str, Any]] = None
    lang_type: Optional[str] = None
    trans: Optional[list[dict[str, Any]]] = None
    sentences: Optional[list[dict[str, Any]]] = None
    phrases: Optional[list[dict[str, Any]]] = None
    entry_type: Optional[str] = None
    sequence: Optional[int] = None


class WordEntryOut(WordEntryBase):
    id: int
    book_id: int
    source_entry_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
