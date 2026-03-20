from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ==================== 分类 Schema ====================

class BaseCategory(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field(default="#3B82F6", max_length=20)
    icon: str = Field(default="tag", max_length=50)
    sort_order: int = Field(default=0)
    owner_id: int


class CategoryCreate(BaseCategory):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    color: Optional[str] = Field(None, max_length=20)
    icon: Optional[str] = Field(None, max_length=50)
    sort_order: Optional[int] = None


class Category(BaseCategory):
    id: int

    class Config:
        from_attributes = True


class CategoryWithTodoCount(Category):
    todo_count: int = 0


# ==================== TODO Schema ====================

class BaseToDo(BaseModel):
    content: str = Field(..., min_length=1, max_length=500)
    done: bool = False
    owner_id: int


class ToDoCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=500)
    done: bool = False
    category_id: Optional[int] = None
    priority: int = Field(default=2, ge=1, le=3)  # 1=低, 2=中, 3=高
    due_date: Optional[datetime] = None
    remind_before: int = Field(default=30, ge=0)  # 提前提醒分钟数


class ToDoUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1, max_length=500)
    done: Optional[bool] = None
    category_id: Optional[int] = None
    priority: Optional[int] = Field(None, ge=1, le=3)
    due_date: Optional[datetime] = None
    remind_before: Optional[int] = Field(None, ge=0)


class ToDo(BaseToDo):
    id: int
    category_id: Optional[int] = None
    priority: int = 2
    due_date: Optional[datetime] = None
    remind_before: int = 30
    is_reminded: bool = False
    created_at: datetime
    completed_at: Optional[datetime] = None
    category: Optional[Category] = None

    class Config:
        from_attributes = True


class ToDoWithStatus(ToDo):
    status: str = "normal"  # overdue, upcoming, normal


class ToDoFilter(BaseModel):
    category_id: Optional[int] = None
    priority: Optional[int] = None
    done: Optional[bool] = None
    status: Optional[str] = None  # overdue, upcoming, normal


# ==================== 统计 Schema ====================

class TodoStats(BaseModel):
    total: int
    completed: int
    pending: int
    overdue: int
    completion_rate: float  # 完成率百分比


class CategoryDistribution(BaseModel):
    category_id: Optional[int]
    category_name: str
    count: int
    color: str


class PriorityDistribution(BaseModel):
    priority: int
    priority_name: str
    count: int


class DailyTrend(BaseModel):
    date: str
    completed: int
    created: int


class TodoStatistics(BaseModel):
    overview: TodoStats
    by_category: List[CategoryDistribution]
    by_priority: List[PriorityDistribution]
    trend_7d: List[DailyTrend]
    trend_30d: List[DailyTrend]


# ==================== 提醒 Schema ====================

class TodoReminder(BaseModel):
    id: int
    content: str
    due_date: Optional[datetime]
    priority: int
    minutes_left: int


class ReminderMessage(BaseModel):
    type: str = "reminder"
    data: TodoReminder
    message: str
