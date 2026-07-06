import mimetypes
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from api.deps import require_admin
from core.config import settings
from models.user import User
from utils.response import BizException, error_response, success_response

router = APIRouter()

_PROJECT_ROOT = settings.resolve_root()
_SOUND_DIR = _PROJECT_ROOT / "sound"
_ARTICLE_DIR = _SOUND_DIR / "article"

_TEXT_EXTENSIONS = {
    ".txt", ".json", ".md", ".markdown", ".log", ".csv", ".xml",
    ".yaml", ".yml", ".js", ".ts", ".jsx", ".tsx", ".py", ".html",
    ".htm", ".css", ".scss", ".ini", ".conf", ".cfg", ".toml",
    ".env", ".sh", ".bat", ".ps1", ".sql", ".java", ".c", ".cpp",
    ".h", ".hpp", ".go", ".rs", ".rb", ".php", ".vue", ".svelte",
    ".mp3", ".wav", ".ogg", ".flac", ".aac",
}

_WORKSPACES = {}


def _init_workspaces():
    """初始化工作区列表。"""
    _WORKSPACES.clear()
    # 默认工作区
    root = Path(settings.file_manager_root)
    if not root.is_absolute():
        root = (_PROJECT_ROOT / root).resolve()
    else:
        root = root.resolve()
    _WORKSPACES["default"] = {"name": "文件管理", "root": root}
    # sound 工作区
    if _SOUND_DIR.exists():
        _WORKSPACES["sound"] = {"name": "文章管理", "root": _SOUND_DIR.resolve()}
    # article 工作区
    if _ARTICLE_DIR.exists():
        _WORKSPACES["article"] = {"name": "文章音频", "root": _ARTICLE_DIR.resolve()}


_init_workspaces()


def _get_workspace(workspace: str = "default") -> dict:
    ws = _WORKSPACES.get(workspace)
    if not ws:
        raise BizException(400, f"未知工作区: {workspace}")
    return ws


def _safe_path(rel_path: str, workspace: str = "default") -> Path:
    """将相对路径解析为绝对路径，并校验必须位于工作区根目录内。"""
    if not rel_path:
        rel_path = "."
    ws = _get_workspace(workspace)
    root = ws["root"]
    target = (root / rel_path).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise BizException(403, "路径越权，禁止访问根目录之外的资源")
    return target


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.2f} MB"
    return f"{size / (1024 * 1024 * 1024):.2f} GB"


@router.get("/workspaces")
async def list_workspaces(_user: User = Depends(require_admin)):
    """返回可用工作区列表。"""
    return success_response([
        {"key": k, "name": v["name"]} for k, v in _WORKSPACES.items()
    ])


@router.get("/list")
async def list_files(
    path: str = Query("", description="相对于根目录的子路径，空表示根目录"),
    workspace: str = Query("default", description="工作区: default / sound"),
    _user: User = Depends(require_admin),
):
    ws = _get_workspace(workspace)
    target = _safe_path(path, workspace)
    if not target.exists():
        return error_response(code=404, message="路径不存在")
    if not target.is_dir():
        return error_response(code=400, message="目标路径不是目录")

    items = []
    try:
        for entry in target.iterdir():
            stat = entry.stat()
            is_dir = entry.is_dir()
            ext = entry.suffix.lower() if not is_dir else ""
            items.append({
                "name": entry.name,
                "path": str(entry.relative_to(ws["root"])).replace("\\", "/"),
                "type": "dir" if is_dir else "file",
                "size": stat.st_size if not is_dir else 0,
                "size_text": _format_size(stat.st_size) if not is_dir else "-",
                "extension": ext,
                "is_text": ext in _TEXT_EXTENSIONS if not is_dir else False,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            })
    except PermissionError:
        return error_response(code=403, message="没有权限读取该目录")

    items.sort(key=lambda x: (x["type"] != "dir", x["name"].lower()))
    rel = str(target.relative_to(ws["root"])).replace("\\", "/")
    return success_response({
        "current_path": rel if rel != "." else "",
        "is_root": target == ws["root"],
        "items": items,
    })


@router.get("/read")
async def read_file(
    path: str = Query(..., description="要查看的文件相对路径"),
    workspace: str = Query("default", description="工作区: default / sound"),
    _user: User = Depends(require_admin),
):
    target = _safe_path(path, workspace)
    if not target.exists():
        return error_response(code=404, message="文件不存在")
    if not target.is_file():
        return error_response(code=400, message="目标路径不是文件")

    size = target.stat().st_size
    if size > settings.file_manager_text_max_size:
        return error_response(
            code=413,
            message=f"文件过大（{_format_size(size)}），超过文本预览上限 "
                    f"{_format_size(settings.file_manager_text_max_size)}，请使用下载功能",
        )

    ext = target.suffix.lower()
    if ext not in _TEXT_EXTENSIONS:
        return error_response(code=415, message=f"不支持预览此类型文件 ({ext or '无扩展名'})，请使用下载功能")

    content = None
    encoding_used = None
    for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030", "latin-1"):
        try:
            content = target.read_text(encoding=enc)
            encoding_used = enc.replace("-sig", "")
            break
        except UnicodeDecodeError:
            continue
    if content is None:
        return error_response(code=422, message="无法解码文件内容，请使用下载功能")

    return success_response({
        "name": target.name,
        "path": path,
        "size": size,
        "size_text": _format_size(size),
        "encoding": encoding_used,
        "extension": ext,
        "content": content,
        "line_count": content.count("\n") + (0 if content.endswith("\n") else 1),
    })


@router.get("/download")
async def download_file(
    path: str = Query(..., description="要下载的文件相对路径"),
    workspace: str = Query("default", description="工作区: default / sound"),
    _user: User = Depends(require_admin),
):
    target = _safe_path(path, workspace)
    if not target.exists():
        return error_response(code=404, message="文件不存在")
    if not target.is_file():
        return error_response(code=400, message="目标路径不是文件")

    media_type, _ = mimetypes.guess_type(target.name)
    if not media_type:
        media_type = "application/octet-stream"
    return FileResponse(
        path=str(target),
        filename=target.name,
        media_type=media_type,
    )
