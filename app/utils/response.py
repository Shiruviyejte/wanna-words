from typing import Any, Optional

from fastapi.responses import JSONResponse


class BizException(Exception):
    """业务异常：被全局异常处理器转换为标准响应 {code, message, data}。"""

    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


def success_response(data: Any = None, message: str = "success") -> dict:
    return {
        "code": 200,
        "message": message,
        "data": data,
    }


def error_response(
    code: int,
    message: str,
    data: Optional[Any] = None,
    status_code: int = 200,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "data": data,
        },
    )


def paginate(items: list, total: int, page: int, page_size: int) -> dict:
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size else 0,
    }
