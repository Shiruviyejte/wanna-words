from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    username: str = Field(..., min_length=2, max_length=100)
    nick_name: str = Field("", max_length=100)
    role: str = Field("user", max_length=20)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=64)


class UserUpdate(BaseModel):
    nick_name: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = Field(None, max_length=20)
    avatar_base64: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6, max_length=64)


class UserOut(UserBase):
    id: int
    avatar_base64: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LoginIn(BaseModel):
    username: str
    password: str


class LoginOut(BaseModel):
    token: str
    user: UserOut


class PasswordChange(BaseModel):
    old_password: str = Field(..., min_length=6, max_length=64)
    new_password: str = Field(..., min_length=6, max_length=64)


class ProfileUpdate(BaseModel):
    nick_name: Optional[str] = Field(None, max_length=100)
    avatar_base64: Optional[str] = None
