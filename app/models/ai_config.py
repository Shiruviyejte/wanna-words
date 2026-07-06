from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class UserAIConfig(Base):
    __tablename__ = "ai_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    base_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    api_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    model: Mapped[str] = mapped_column(String(50), nullable=False, default="deepseek-chat")
    is_default_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
