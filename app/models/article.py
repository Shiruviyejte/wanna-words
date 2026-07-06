from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Article(Base):
    __tablename__ = "article"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("article_books.id", ondelete="SET NULL"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False, default="story")
    input: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    title_en: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    title_zh: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    content_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    content_zh: Mapped[str] = mapped_column(Text, nullable=False, default="")
    audio_src: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    lrc_position: Mapped[list | None] = mapped_column(JSON, nullable=True)
    question: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    name_list: Mapped[list | None] = mapped_column(JSON, nullable=True)
    quote: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="deepseek-chat")
    gen_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gen_input: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ai_response: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    book = relationship("ArticleBook", back_populates="articles")
