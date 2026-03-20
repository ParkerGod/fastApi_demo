from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CategoryBase(BaseModel):
    name: str
    color: str = "#3B82F6"
    icon: str = "folder"
    sort_order: int = 0


class CategoryCreate(CategoryBase):
    owner_id: int


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None


class Category(CategoryBase):
    id: int
    owner_id: int

    class Config:
        orm_mode = True


class ToDoStatus(str):
    overdue = "overdue"
    upcoming = "upcoming"
    normal = "normal"


class BaseToDo(BaseModel):
    content: str
    done: bool = False
    owner_id: int
    category_id: Optional[int] = None
    priority: int = Field(default=2, ge=1, le=3, description="优先级: 1=低, 2=中, 3=高")
    due_date: Optional[datetime] = None
    remind_before: int = 30


class ToDoCreate(BaseToDo):
    pass


class ToDoUpdate(BaseModel):
    content: Optional[str] = None
    done: Optional[bool] = None
    category_id: Optional[int] = None
    priority: Optional[int] = Field(default=None, ge=1, le=3, description="优先级: 1=低, 2=中, 3=高")
    due_date: Optional[datetime] = None
    remind_before: Optional[int] = None


class ToDoResponse(BaseToDo):
    id: int
    is_reminded: bool = False
    created_at: datetime

    class Config:
        orm_mode = True


class ToDoWithStatus(ToDoResponse):
    status: str

    class Config:
        orm_mode = True


class CategoryWithTodos(Category):
    todos: List[ToDoResponse] = []

    class Config:
        orm_mode = True


class StatisticsBase(BaseModel):
    total: int
    completed: int
    completion_rate: float


class CategoryDistribution(BaseModel):
    category_id: Optional[int]
    category_name: Optional[str]
    total: int
    completed: int


class PriorityDistribution(BaseModel):
    priority: int
    total: int
    completed: int


class TrendData(BaseModel):
    date: str
    completed: int


class StatisticsResponse(BaseModel):
    completion_rate: float
    category_distribution: List[CategoryDistribution]
    priority_distribution: List[PriorityDistribution]
    trend_7_days: List[TrendData]
    trend_30_days: List[TrendData]
