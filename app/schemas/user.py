from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class UserAdminCreate(BaseModel):
    """SuperAdmin can create users with any role"""

    email: EmailStr
    password: str
    full_name: str
    role: str = "USER"
    is_active: bool = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: str
    point_balance: int
    is_active: bool

    class Config:
        from_attributes = True


class UserReadFull(UserRead):
    created_at: datetime
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    point_balance: Optional[int] = None


class UserDeleteResponse(BaseModel):
    message: str
    user_id: UUID
