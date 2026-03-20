from pydantic import BaseModel
from typing import Optional


class UserBase(BaseModel):
    email: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    username: str
    avatar: Optional[str] = None
    role: str
    is_active: bool
    frequency_max: int

    class Config:
        orm_mode = True


class UserPassWord(BaseModel):
    id: int
    oldpassword: str
    password: str
