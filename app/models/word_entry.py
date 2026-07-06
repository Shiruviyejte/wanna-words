from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class WordEntry(Base):
    __tablename__ = "word_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    book_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("word_books.id", ondelete="CASCADE"), nullable=False
    )
    source_entry_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    word: Mapped[str] = mapped_column(String(120), nullable=False)
    phonetic0: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    phonetic1: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    synos: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    etymology: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    inflections: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    e2e: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    exams_src: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    rel_words: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    lang_type: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    trans: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    sentences: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    phrases: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False, default="word")
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    book = relationship("WordBook", back_populates="words")
