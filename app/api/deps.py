from collections.abc import AsyncGenerator

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import decode_access_token
from core.config import settings
from core.database import SessionLocal
from models.user import User
from utils.response import BizException


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise BizException(401, "未携带认证令牌")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
    except Exception:
        raise BizException(401, "令牌无效或已过期")

    user_id = payload.get("sub")
    if not user_id:
        raise BizException(401, "令牌缺少用户标识")

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise BizException(401, "用户不存在")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise BizException(403, "需要管理员权限")
    return user


def _match_whitelist(path: str) -> bool:
    """检查请求路径是否在白名单中（支持前缀匹配）。"""
    for pattern in settings.whitelist_paths:
        if path.startswith(pattern):
            return True
    return False


async def require_user(
    request: Request,
    user: User = Depends(get_current_user),
) -> User:
    """白名单权限：admin 可访问所有，普通用户仅可访问白名单路径。"""
    if user.role == "admin":
        return user
    if _match_whitelist(request.url.path):
        return user
    raise BizException(403, "需要管理员权限")
