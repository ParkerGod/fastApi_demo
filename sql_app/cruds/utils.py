from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Optional, List
from .. import models
from ..schemas import schemas_utils


def get_todo_status(due_date: Optional[datetime], done: bool) -> str:
    if done:
        return "normal"
    if due_date is None:
        return "normal"
    
    now = datetime.utcnow()
    if due_date < now:
        return "overdue"
    if due_date - now <= timedelta(days=1):
        return "upcoming"
    return "normal"


def get_categories(db: Session, owner_id: int) -> List[models.Category]:
    return db.query(models.Category).filter(
        models.Category.owner_id == owner_id
    ).order_by(models.Category.sort_order).all()


def get_category(db: Session, category_id: int, owner_id: int) -> Optional[models.Category]:
    return db.query(models.Category).filter(
        and_(
            models.Category.id == category_id,
            models.Category.owner_id == owner_id
        )
    ).first()


def create_category(db: Session, category_data: schemas_utils.CategoryCreate) -> models.Category:
    db_category = models.Category(
        name=category_data.name,
        color=category_data.color,
        icon=category_data.icon,
        sort_order=category_data.sort_order,
        owner_id=category_data.owner_id
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


def update_category(db: Session, category_id: int, owner_id: int, 
                   category_data: schemas_utils.CategoryUpdate) -> Optional[models.Category]:
    category = get_category(db, category_id, owner_id)
    if not category:
        return None
    
    update_data = category_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)
    
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int, owner_id: int) -> int:
    return db.query(models.Category).filter(
        and_(
            models.Category.id == category_id,
            models.Category.owner_id == owner_id
        )
    ).delete()


def get_todo(db: Session, uid: int, category_id: Optional[int] = None,
             priority: Optional[int] = None, include_done: bool = True) -> List[models.ToDo]:
    query = db.query(models.ToDo).filter(models.ToDo.owner_id == uid)
    
    if category_id is not None:
        query = query.filter(models.ToDo.category_id == category_id)
    
    if priority is not None:
        query = query.filter(models.ToDo.priority == priority)
    
    if not include_done:
        query = query.filter(models.ToDo.done == False)
    
    query = query.order_by(
        models.ToDo.priority.desc(),
        models.ToDo.due_date.asc().nullslast(),
        models.ToDo.created_at.desc()
    )
    
    return query.all()


def get_todo_by_id(db: Session, todo_id: int, owner_id: int) -> Optional[models.ToDo]:
    return db.query(models.ToDo).filter(
        and_(
            models.ToDo.id == todo_id,
            models.ToDo.owner_id == owner_id
        )
    ).first()


def create_todo(db: Session, todo_data: schemas_utils.ToDoCreate) -> models.ToDo:
    db_todo = models.ToDo(
        content=todo_data.content,
        done=todo_data.done,
        owner_id=todo_data.owner_id,
        category_id=todo_data.category_id,
        priority=todo_data.priority,
        due_date=todo_data.due_date,
        remind_before=todo_data.remind_before
    )
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    return db_todo


def update_todo(db: Session, todo_id: int, owner_id: int,
               todo_data: schemas_utils.ToDoUpdate) -> Optional[models.ToDo]:
    todo = get_todo_by_id(db, todo_id, owner_id)
    if not todo:
        return None
    
    update_data = todo_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(todo, key, value)
    
    db.commit()
    db.refresh(todo)
    return todo


def delete_todo(db: Session, todo_id: int, owner_id: int) -> int:
    return db.query(models.ToDo).filter(
        and_(
            models.ToDo.id == todo_id,
            models.ToDo.owner_id == owner_id
        )
    ).delete()


def get_todos_for_reminder(db: Session) -> List[models.ToDo]:
    now = datetime.utcnow()
    
    todos = db.query(models.ToDo).filter(
        and_(
            models.ToDo.done == False,
            models.ToDo.due_date.isnot(None),
            models.ToDo.is_reminded == False
        )
    ).all()
    
    result = []
    for todo in todos:
        remind_time = todo.due_date - timedelta(minutes=todo.remind_before)
        if now >= remind_time:
            result.append(todo)
    
    return result


def mark_todo_reminded(db: Session, todo_id: int) -> None:
    db.query(models.ToDo).filter(models.ToDo.id == todo_id).update(
        {"is_reminded": True}
    )
    db.commit()


def get_statistics(db: Session, owner_id: int) -> schemas_utils.StatisticsResponse:
    todos = db.query(models.ToDo).filter(models.ToDo.owner_id == owner_id).all()
    
    total = len(todos)
    completed = sum(1 for t in todos if t.done)
    completion_rate = round(completed / total * 100, 2) if total > 0 else 0.0
    
    categories = db.query(models.Category).filter(
        models.Category.owner_id == owner_id
    ).all()
    
    category_distribution = []
    for cat in categories:
        cat_todos = [t for t in todos if t.category_id == cat.id]
        cat_completed = sum(1 for t in cat_todos if t.done)
        category_distribution.append(
            schemas_utils.CategoryDistribution(
                category_id=cat.id,
                category_name=cat.name,
                total=len(cat_todos),
                completed=cat_completed
            )
        )
    
    uncategorized_todos = [t for t in todos if t.category_id is None]
    if uncategorized_todos:
        uncategorized_completed = sum(1 for t in uncategorized_todos if t.done)
        category_distribution.append(
            schemas_utils.CategoryDistribution(
                category_id=None,
                category_name=None,
                total=len(uncategorized_todos),
                completed=uncategorized_completed
            )
        )
    
    priority_distribution = []
    for p in [1, 2, 3]:
        pri_todos = [t for t in todos if t.priority == p]
        pri_completed = sum(1 for t in pri_todos if t.done)
        priority_distribution.append(
            schemas_utils.PriorityDistribution(
                priority=p,
                total=len(pri_todos),
                completed=pri_completed
            )
        )
    
    trend_7_days = _get_trend_data(db, owner_id, 7)
    trend_30_days = _get_trend_data(db, owner_id, 30)
    
    return schemas_utils.StatisticsResponse(
        completion_rate=completion_rate,
        category_distribution=category_distribution,
        priority_distribution=priority_distribution,
        trend_7_days=trend_7_days,
        trend_30_days=trend_30_days
    )


def _get_trend_data(db: Session, owner_id: int, days: int) -> List[schemas_utils.TrendData]:
    result = []
    today = datetime.utcnow().date()
    
    for i in range(days - 1, -1, -1):
        date = today - timedelta(days=i)
        next_date = date + timedelta(days=1)
        
        completed = db.query(func.count(models.ToDo.id)).filter(
            and_(
                models.ToDo.owner_id == owner_id,
                models.ToDo.done == True,
                models.ToDo.updated_at >= datetime.combine(date, datetime.min.time()),
                models.ToDo.updated_at < datetime.combine(next_date, datetime.min.time())
            )
        ).scalar() or 0
        
        result.append(schemas_utils.TrendData(
            date=date.strftime("%Y-%m-%d"),
            completed=completed
        ))
    
    return result
