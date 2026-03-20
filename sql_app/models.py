from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


# 数据库模型
# 用户表
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String)
    avatar = Column(String, default=None)
    hashed_password = Column(String)
    role = Column(String, default="general")
    is_active = Column(Boolean, default=True)
    frequency_max = Column(Integer, default=600)

    todos = relationship("ToDo", back_populates="owner_todo")
    categories = relationship("Category", back_populates="owner_category")


# 分类表
class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    color = Column(String, default="#3B82F6")
    icon = Column(String, default="folder")
    sort_order = Column(Integer, default=0)
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner_category = relationship("User", back_populates="categories")
    todos = relationship("ToDo", back_populates="category")


# TODO表
class ToDo(Base):
    __tablename__ = "todo_info"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    done = Column(Boolean, default=False)
    priority = Column(Integer, default=2)
    due_date = Column(DateTime, default=None)
    remind_before = Column(Integer, default=0)
    is_reminded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id"))
    category_id = Column(Integer, ForeignKey("categories.id"), default=None)

    owner_todo = relationship("User", back_populates="todos")
    category = relationship("Category", back_populates="todos")
