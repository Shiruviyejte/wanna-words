from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from core.auth import create_access_token, verify_password
from models.user import User
from schemas.user import LoginIn, LoginOut, UserOut
from utils.response import error_response, success_response

router = APIRouter()


@router.post("/login")
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == payload.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        return error_response(code=401, message="用户名或密码错误")
    token = create_access_token(
        subject=str(user.id),
        extra_claims={"username": user.username, "role": user.role},
    )
    data = LoginOut(token=token, user=UserOut.model_validate(user, from_attributes=True))
    return success_response(data.model_dump(mode="json"))


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return success_response(UserOut.model_validate(user, from_attributes=True).model_dump(mode="json"))
