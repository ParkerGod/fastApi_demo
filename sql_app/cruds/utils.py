from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from .. import models
from ..schemas import schemas_utils


# ==================== TODO CRUD ====================

def _calculate_status(todo: models.ToDo) -> str:
    """计算TODO的状态"""
    if todo.done:
        return "normal"
    if not todo.due_date:
        return "normal"
    
    now = datetime.utcnow()
    if todo.due_date < now:
        return "overdue"
    
    upcoming_time = now + timedelta(hours=24)
    if todo.due_date <= upcoming_time:
        return "upcoming"
    
    return "normal"


def _todo_to_dict_with_status(todo: models.ToDo) -> dict:
    """将TODO转换为字典并添加status字段"""
    from sqlalchemy.orm import class_mapper
    
    # 获取所有列属性
    columns = [c.key for c in class_mapper(models.ToDo).columns]
    
    # 基础字段
    todo_dict = {c: getattr(todo, c) for c in columns}
    
    # 添加category关系
    if todo.category:
        todo_dict["category"] = {
            "id": todo.category.id,
            "name": todo.category.name,
            "color": todo.category.color,
            "icon": todo.category.icon,
            "sort_order": todo.category.sort_order,
            "owner_id": todo.category.owner_id
        }
    else:
        todo_dict["category"] = None
    
    # 计算并添加status
    todo_dict["status"] = _calculate_status(todo)
    
    return todo_dict


def get_todo(db: Session, uid: int, filters: Optional[schemas_utils.ToDoFilter] = None):
    """根据用户ID获取TODO信息，支持筛选"""
    query = db.query(models.ToDo).filter(models.ToDo.owner_id == uid)

    if filters:
        if filters.category_id is not None:
            query = query.filter(models.ToDo.category_id == filters.category_id)
        if filters.priority is not None:
            query = query.filter(models.ToDo.priority == filters.priority)
        if filters.done is not None:
            query = query.filter(models.ToDo.done == filters.done)
        if filters.status:
            now = datetime.utcnow()
            if filters.status == "overdue":
                query = query.filter(
                    models.ToDo.due_date < now,
                    models.ToDo.done == False
                )
            elif filters.status == "upcoming":
                upcoming_time = now + timedelta(hours=24)
                query = query.filter(
                    models.ToDo.due_date >= now,
                    models.ToDo.due_date <= upcoming_time,
                    models.ToDo.done == False
                )
            elif filters.status == "normal":
                query = query.filter(
                    or_(
                        models.ToDo.due_date == None,
                        models.ToDo.due_date > datetime.utcnow() + timedelta(hours=24),
                        models.ToDo.done == True
                    )
                )

    # 默认排序：优先级降序 -> 截止日期升序 -> 创建时间降序
    query = query.order_by(
        models.ToDo.priority.desc(),
        models.ToDo.due_date.asc().nullslast(),
        models.ToDo.created_at.desc()
    )

    return query.all()


def get_todo_with_status(db: Session, uid: int, filters: Optional[schemas_utils.ToDoFilter] = None) -> List[dict]:
    """根据用户ID获取TODO信息，支持筛选，返回包含status字段"""
    todos = get_todo(db, uid, filters)
    return [_todo_to_dict_with_status(todo) for todo in todos]


def get_todo_by_id(db: Session, todo_id: int, uid: int):
    """根据ID获取单个TODO"""
    return db.query(models.ToDo).filter(
        models.ToDo.id == todo_id,
        models.ToDo.owner_id == uid
    ).first()


def create_todo(db: Session, todo_data: schemas_utils.ToDoCreate, uid: int):
    """创建TODO信息"""
    db_todo = models.ToDo(
        content=todo_data.content,
        done=todo_data.done,
        owner_id=uid,
        category_id=todo_data.category_id,
        priority=todo_data.priority,
        due_date=todo_data.due_date,
        remind_before=todo_data.remind_before
    )
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    return db_todo


def delete_todo(db: Session, todo_id: int, uid: int):
    """删除TODO信息"""
    res = db.query(models.ToDo).filter(
        models.ToDo.id == todo_id,
        models.ToDo.owner_id == uid
    ).delete()
    db.commit()
    return res


def update_todo(db: Session, todo_id: int, todo_data: schemas_utils.ToDoUpdate, uid: int):
    """修改TODO信息"""
    todo = db.query(models.ToDo).filter(
        models.ToDo.id == todo_id,
        models.ToDo.owner_id == uid
    ).first()

    if not todo:
        return None

    update_data = todo_data.dict(exclude_unset=True)

    # 如果标记为完成，设置完成时间
    if update_data.get("done") == True and not todo.done:
        update_data["completed_at"] = datetime.utcnow()
    elif update_data.get("done") == False:
        update_data["completed_at"] = None

    for key, value in update_data.items():
        setattr(todo, key, value)

    db.commit()
    db.refresh(todo)
    return todo


# ==================== Category CRUD ====================

def get_categories(db: Session, uid: int):
    """获取用户的所有分类"""
    return db.query(models.Category).filter(
        models.Category.owner_id == uid
    ).order_by(models.Category.sort_order.asc()).all()


def get_category_by_id(db: Session, category_id: int, uid: int):
    """根据ID获取分类"""
    return db.query(models.Category).filter(
        models.Category.id == category_id,
        models.Category.owner_id == uid
    ).first()


def create_category(db: Session, category_data: schemas_utils.CategoryCreate):
    """创建分类"""
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


def update_category(db: Session, category_id: int, category_data: schemas_utils.CategoryUpdate, uid: int):
    """更新分类"""
    category = db.query(models.Category).filter(
        models.Category.id == category_id,
        models.Category.owner_id == uid
    ).first()

    if not category:
        return None

    update_data = category_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)

    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int, uid: int):
    """删除分类，将该分类下的TODO设为无分类"""
    # 先将该分类下的TODO的category_id设为None
    db.query(models.ToDo).filter(
        models.ToDo.category_id == category_id,
        models.ToDo.owner_id == uid
    ).update({"category_id": None})

    # 删除分类
    res = db.query(models.Category).filter(
        models.Category.id == category_id,
        models.Category.owner_id == uid
    ).delete()

    db.commit()
    return res


def get_category_with_todo_count(db: Session, uid: int):
    """获取分类及其TODO数量"""
    categories = db.query(
        models.Category,
        func.count(models.ToDo.id).label("todo_count")
    ).outerjoin(
        models.ToDo,
        models.Category.id == models.ToDo.category_id
    ).filter(
        models.Category.owner_id == uid
    ).group_by(
        models.Category.id
    ).order_by(
        models.Category.sort_order.asc()
    ).all()

    return categories


# ==================== Statistics CRUD ====================

def get_todo_statistics(db: Session, uid: int):
    """获取TODO统计信息"""
    now = datetime.utcnow()

    # 基础统计
    total = db.query(models.ToDo).filter(models.ToDo.owner_id == uid).count()
    completed = db.query(models.ToDo).filter(
        models.ToDo.owner_id == uid,
        models.ToDo.done == True
    ).count()
    pending = total - completed
    overdue = db.query(models.ToDo).filter(
        models.ToDo.owner_id == uid,
        models.ToDo.done == False,
        models.ToDo.due_date < now
    ).count()

    completion_rate = round((completed / total * 100), 2) if total > 0 else 0.0

    overview = schemas_utils.TodoStats(
        total=total,
        completed=completed,
        pending=pending,
        overdue=overdue,
        completion_rate=completion_rate
    )

    # 按分类分布
    category_dist = db.query(
        models.Category.id.label("category_id"),
        models.Category.name.label("category_name"),
        models.Category.color.label("color"),
        func.count(models.ToDo.id).label("count")
    ).outerjoin(
        models.ToDo,
        and_(
            models.Category.id == models.ToDo.category_id,
            models.ToDo.owner_id == uid
        )
    ).filter(
        models.Category.owner_id == uid
    ).group_by(
        models.Category.id
    ).all()

    by_category = [
        schemas_utils.CategoryDistribution(
            category_id=item.category_id,
            category_name=item.category_name,
            count=item.count,
            color=item.color
        ) for item in category_dist
    ]

    # 添加无分类的统计
    no_category_count = db.query(models.ToDo).filter(
        models.ToDo.owner_id == uid,
        models.ToDo.category_id == None
    ).count()

    if no_category_count > 0:
        by_category.append(schemas_utils.CategoryDistribution(
            category_id=None,
            category_name="未分类",
            count=no_category_count,
            color="#9CA3AF"
        ))

    # 按优先级分布
    priority_names = {1: "低", 2: "中", 3: "高"}
    priority_dist = db.query(
        models.ToDo.priority,
        func.count(models.ToDo.id).label("count")
    ).filter(
        models.ToDo.owner_id == uid
    ).group_by(
        models.ToDo.priority
    ).all()

    by_priority = [
        schemas_utils.PriorityDistribution(
            priority=item.priority,
            priority_name=priority_names.get(item.priority, "未知"),
            count=item.count
        ) for item in priority_dist
    ]

    # 近7天趋势
    trend_7d = []
    for i in range(6, -1, -1):
        date = now - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        date_start = datetime(date.year, date.month, date.day, 0, 0, 0)
        date_end = datetime(date.year, date.month, date.day, 23, 59, 59)

        completed_count = db.query(models.ToDo).filter(
            models.ToDo.owner_id == uid,
            models.ToDo.done == True,
            models.ToDo.completed_at >= date_start,
            models.ToDo.completed_at <= date_end
        ).count()

        created_count = db.query(models.ToDo).filter(
            models.ToDo.owner_id == uid,
            models.ToDo.created_at >= date_start,
            models.ToDo.created_at <= date_end
        ).count()

        trend_7d.append(schemas_utils.DailyTrend(
            date=date_str,
            completed=completed_count,
            created=created_count
        ))

    # 近30天趋势
    trend_30d = []
    for i in range(29, -1, -1):
        date = now - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        date_start = datetime(date.year, date.month, date.day, 0, 0, 0)
        date_end = datetime(date.year, date.month, date.day, 23, 59, 59)

        completed_count = db.query(models.ToDo).filter(
            models.ToDo.owner_id == uid,
            models.ToDo.done == True,
            models.ToDo.completed_at >= date_start,
            models.ToDo.completed_at <= date_end
        ).count()

        created_count = db.query(models.ToDo).filter(
            models.ToDo.owner_id == uid,
            models.ToDo.created_at >= date_start,
            models.ToDo.created_at <= date_end
        ).count()

        trend_30d.append(schemas_utils.DailyTrend(
            date=date_str,
            completed=completed_count,
            created=created_count
        ))

    return schemas_utils.TodoStatistics(
        overview=overview,
        by_category=by_category,
        by_priority=by_priority,
        trend_7d=trend_7d,
        trend_30d=trend_30d
    )


# ==================== Reminder CRUD ====================

def get_upcoming_reminders(db: Session, uid: int, max_check_minutes: int = 1440):
    """获取即将到期的TODO（用于提醒）
    
    根据每项TODO的 remind_before 字段个性化提醒
    max_check_minutes: 最大检查时间范围（默认24小时）
    """
    now = datetime.utcnow()
    max_upcoming_time = now + timedelta(minutes=max_check_minutes)

    # 获取所有未完成的、有截止日期的、未提醒的TODO
    todos = db.query(models.ToDo).filter(
        models.ToDo.owner_id == uid,
        models.ToDo.done == False,
        models.ToDo.is_reminded == False,
        models.ToDo.due_date != None,
        models.ToDo.due_date > now,
        models.ToDo.due_date <= max_upcoming_time
    ).all()

    # 根据每项TODO的 remind_before 筛选出需要提醒的
    reminders = []
    for todo in todos:
        remind_time = todo.due_date - timedelta(minutes=todo.remind_before)
        # 如果当前时间已经过了提醒时间，且还没到截止日期
        if now >= remind_time and now < todo.due_date:
            reminders.append(todo)

    return reminders


def mark_reminded(db: Session, todo_id: int, uid: int):
    """标记TODO为已提醒"""
    todo = db.query(models.ToDo).filter(
        models.ToDo.id == todo_id,
        models.ToDo.owner_id == uid
    ).first()

    if todo:
        todo.is_reminded = True
        db.commit()
        db.refresh(todo)

    return todo


def reset_reminder(db: Session, todo_id: int, uid: int):
    """重置提醒状态（当修改截止日期时）"""
    todo = db.query(models.ToDo).filter(
        models.ToDo.id == todo_id,
        models.ToDo.owner_id == uid
    ).first()

    if todo:
        todo.is_reminded = False
        db.commit()
        db.refresh(todo)

    return todo
