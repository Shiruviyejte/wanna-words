import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.v1 import ai_config, article, article_book, auth, dashboard, file_manager, sound, translate, user, word, wordbook
from core.config import settings
from utils.response import BizException, error_response, success_response

app = FastAPI(title=settings.app_name, docs_url="/docs", openapi_url="/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(BizException)
async def biz_exception_handler(request: Request, exc: BizException):
    return error_response(code=exc.code, message=exc.message, data=exc.data)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return error_response(code=422, message="参数校验失败", data=exc.errors())


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if settings.debug:
        import traceback

        return error_response(code=500, message=f"服务器内部错误: {exc}", data=traceback.format_exc())
    return error_response(code=500, message="服务器内部错误")


api_prefix = settings.api_prefix
app.include_router(auth.router, prefix=f"{api_prefix}/auth", tags=["认证"])
app.include_router(user.router, prefix=f"{api_prefix}/users", tags=["用户"])
app.include_router(wordbook.router, prefix=f"{api_prefix}/wordbooks", tags=["词库管理"])
app.include_router(word.router, prefix=f"{api_prefix}/words", tags=["单词管理"])
app.include_router(article_book.router, prefix=f"{api_prefix}/article-books", tags=["文章本管理"])
app.include_router(article.router, prefix=f"{api_prefix}/articles", tags=["文章管理"])
app.include_router(ai_config.router, prefix=f"{api_prefix}/ai-configs", tags=["AI 配置"])
app.include_router(file_manager.router, prefix=f"{api_prefix}/files", tags=["文件管理"])
app.include_router(translate.router, prefix=f"{api_prefix}/translate", tags=["翻译与发音"])
app.include_router(dashboard.router, prefix=f"{api_prefix}/dashboard", tags=["仪表盘"])
app.include_router(sound.router, prefix=f"{api_prefix}/sound", tags=["音频文件"])


@app.get(f"{api_prefix}/health")
async def health():
    return success_response({"status": "ok"})


static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="admin")


if __name__ == "__main__":
    import logging
    import uvicorn

    class _IgnoreClientDisconnect(logging.Filter):
        """过滤客户端主动断开连接导致的 uvicorn traceback 噪音日志。"""

        _IGNORED = (
            ConnectionResetError,
            ConnectionAbortedError,
            BrokenPipeError,
        )

        def filter(self, record: logging.LogRecord) -> bool:
            if record.exc_info:
                exc = record.exc_info[1]
                if isinstance(exc, self._IGNORED):
                    return False
            msg = record.getMessage()
            if "ConnectionResetError" in msg or "WinError 10054" in msg or "WinError 1236" in msg:
                return False
            return True

    for name in ("uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).addFilter(_IgnoreClientDisconnect())

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info",
    )
