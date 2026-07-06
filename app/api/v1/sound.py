import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from api.deps import get_current_user
from core.config import settings
from models.user import User

router = APIRouter()

SOUND_DIR = settings.resolve_root() / "sound"


@router.get("/{file_path:path}")
async def serve_sound(file_path: str, _user: User = Depends(get_current_user)):
    """转发本地音频文件，需要 Token 认证。"""
    safe_path = os.path.normpath(file_path)
    # 防止路径穿越攻击
    if safe_path.startswith("..") or os.path.isabs(safe_path):
        raise HTTPException(status_code=400, detail="非法文件路径")
    full_path = (SOUND_DIR / safe_path).resolve()
    # 确保解析后的路径在 SOUND_DIR 内
    if not str(full_path).startswith(str(SOUND_DIR.resolve())):
        raise HTTPException(status_code=400, detail="非法文件路径")
    if not full_path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(full_path, media_type="audio/mpeg")
