from typing import Any, Optional

from pydantic import BaseModel


class PageQuery(BaseModel):
    page: int = 1
    page_size: int = 20
    keyword: Optional[str] = None


class PageResult(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
