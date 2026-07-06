from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, require_admin
from core.auth import hash_password, verify_password
from models.user import User
from schemas.user import PasswordChange, ProfileUpdate, UserCreate, UserOut, UserUpdate
from utils.response import error_response, paginate, success_response

router = APIRouter()


@router.get("")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
):
    stmt = select(User)
    count_stmt = select(func.count(User.id))
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(User.username.like(like) | User.nick_name.like(like))
        count_stmt = count_stmt.where(User.username.like(like) | User.nick_name.like(like))

    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(User.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    items = [UserOut.model_validate(u, from_attributes=True).model_dump(mode="json") for u in rows]
    return success_response(paginate(items, total, page, page_size))


@router.post("")
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
):
    exists = await db.execute(select(User).where(User.username == payload.username))
    if exists.scalar_one_or_none():
        return error_response(code=400, message="用户名已存在")
    user = User(
        username=payload.username,
        nick_name=payload.nick_name,
        role=payload.role,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return success_response(UserOut.model_validate(user, from_attributes=True).model_dump(mode="json"))


@router.put("/password")
async def change_password(
    payload: PasswordChange,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(payload.old_password, user.password_hash):
        return error_response(code=400, message="原密码错误")
    if payload.old_password == payload.new_password:
        return error_response(code=400, message="新密码不能与旧密码相同")
    user.password_hash = hash_password(payload.new_password)
    await db.commit()
    return success_response(message="密码已修改")


@router.put("/profile")
async def update_profile(
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.nick_name is not None:
        user.nick_name = payload.nick_name
    if payload.avatar_base64 is not None:
        user.avatar_base64 = payload.avatar_base64
    await db.commit()
    await db.refresh(user)
    return success_response(UserOut.model_validate(user, from_attributes=True).model_dump(mode="json"))


@router.get("/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db), _user: User = Depends(require_admin)):
    user = await db.get(User, user_id)
    if not user:
        return error_response(code=404, message="用户不存在")
    return success_response(UserOut.model_validate(user, from_attributes=True).model_dump(mode="json"))


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    user = await db.get(User, user_id)
    if not user:
        return error_response(code=404, message="用户不存在")
    if current.role != "admin" and current.id != user.id:
        return error_response(code=403, message="无权修改他人信息")

    data = payload.model_dump(exclude_unset=True)
    if "password" in data:
        if data["password"]:
            user.password_hash = hash_password(data["password"])
        data.pop("password")
    if "role" in data and current.role != "admin":
        data.pop("role")
    for k, v in data.items():
        setattr(user, k, v)
    await db.commit()
    await db.refresh(user)
    return success_response(UserOut.model_validate(user, from_attributes=True).model_dump(mode="json"))


@router.delete("/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db), _user: User = Depends(require_admin)):
    user = await db.get(User, user_id)
    if not user:
        return error_response(code=404, message="用户不存在")
    await db.delete(user)
    await db.commit()
    return success_response(message="已删除")
