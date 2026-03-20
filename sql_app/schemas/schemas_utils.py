from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict


# 分类模型
class CategoryBase(BaseModel):
    name: str
    color: Optional[str] = "#3B82F6"
    icon: Optional[str] = "folder"
    sort_order: Optional[int] = 0


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(CategoryBase):
    name: Optional[str] = None


class Category(CategoryBase):
    id: int
    owner_id: int

    class Config:
        from_attributes = True


# TODO状态枚举
class TodoStatus(str):
    OVERDUE = "overdue"
    UPCOMING = "upcoming"
    NORMAL = "normal"


# TODO模型
class ToDoBase(BaseModel):
    content: str
    done: bool = False
    priority: Optional[int] = 2
    due_date: Optional[datetime] = None
    remind_before: Optional[int] = 0
    category_id: Optional[int] = None


class ToDoCreate(ToDoBase):
    pass


class ToDoUpdate(ToDoBase):
    content: Optional[str] = None
    done: Optional[bool] = None
    priority: Optional[int] = None
    is_reminded: Optional[bool] = None


class ToDo(ToDoBase):
    id: int
    owner_id: int
    created_at: datetime
    is_reminded: bool
    status: Optional[str] = None
    category: Optional[Category] = None

    class Config:
        from_attributes = True


# 统计模型
class TodoStats(BaseModel):
    total: int
    completed: int
    pending: int
    completion_rate: float
    overdue: int
    upcoming: int


class CategoryDistribution(BaseModel):
    category_id: int
    category_name: str
    count: int


class PriorityDistribution(BaseModel):
    priority: int
    count: int


class TrendData(BaseModel):
    date: str
    completed: int


class StatsResponse(BaseModel):
    overview: TodoStats
    by_category: List[CategoryDistribution]
    by_priority: List[PriorityDistribution]
    trend_7days: List[TrendData]
    trend_30days: List[TrendData]
