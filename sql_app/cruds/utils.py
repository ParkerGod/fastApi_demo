from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc, asc
from datetime import datetime, timedelta
from typing import List, Optional

from .. import models
from ..schemas import schemas_utils


'''
# 分类管理
'''


# 创建分类
def create_category(db: Session, category_data: schemas_utils.CategoryCreate, owner_id: int):
    db_category = models.Category(
        name=category_data.name,
        color=category_data.color,
        icon=category_data.icon,
        sort_order=category_data.sort_order,
        owner_id=owner_id
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


# 获取用户所有分类
def get_categories(db: Session, owner_id: int):
    return db.query(models.Category).filter(models.Category.owner_id == owner_id).order_by(models.Category.sort_order).all()


# 获取单个分类
def get_category(db: Session, category_id: int, owner_id: int):
    return db.query(models.Category).filter(models.Category.id == category_id, models.Category.owner_id == owner_id).first()


# 更新分类
def update_category(db: Session, category_id: int, category_data: schemas_utils.CategoryUpdate, owner_id: int):
    db_category = get_category(db, category_id, owner_id)
    if not db_category:
        return None
    
    update_data = category_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_category, key, value)
    
    db.commit()
    db.refresh(db_category)
    return db_category


# 删除分类
def delete_category(db: Session, category_id: int, owner_id: int):
    # 先将该分类下的TODO设置为无分类
    db.query(models.ToDo).filter(models.ToDo.category_id == category_id, models.ToDo.owner_id == owner_id).update({"category_id": None})
    # 删除分类
    res = db.query(models.Category).filter(models.Category.id == category_id, models.Category.owner_id == owner_id).delete()
    db.commit()
    return res


'''
# TODO管理
'''


# 计算TODO状态
def calculate_todo_status(todo: models.ToDo) -> str:
    now = datetime.utcnow()
    
    if todo.done:
        return schemas_utils.TodoStatus.NORMAL
    
    if todo.due_date:
        # 已过期
        if todo.due_date < now:
            return schemas_utils.TodoStatus.OVERDUE
        
        # 即将过期（提醒时间内）
        if todo.remind_before > 0:
            remind_time = todo.due_date - timedelta(minutes=todo.remind_before)
            if now >= remind_time:
                return schemas_utils.TodoStatus.UPCOMING
    
    return schemas_utils.TodoStatus.NORMAL


# 为TODO列表添加状态信息
def add_todo_status(todos: List[models.ToDo]) -> List[dict]:
    result = []
    for todo in todos:
        todo_dict = {
            "id": todo.id,
            "content": todo.content,
            "done": todo.done,
            "priority": todo.priority,
            "due_date": todo.due_date,
            "remind_before": todo.remind_before,
            "is_reminded": todo.is_reminded,
            "created_at": todo.created_at,
            "owner_id": todo.owner_id,
            "category_id": todo.category_id,
            "category": todo.category,
            "status": calculate_todo_status(todo)
        }
        result.append(todo_dict)
    return result


# 根据用户ID获取TODO信息（支持筛选和排序）
def get_todos(
    db: Session, 
    uid: int, 
    category_id: Optional[int] = None,
    priority: Optional[int] = None,
    done: Optional[bool] = None,
    status: Optional[str] = None,
    sort_by: Optional[str] = None
):
    query = db.query(models.ToDo).filter(models.ToDo.owner_id == uid)
    
    # 筛选条件
    if category_id is not None:
        query = query.filter(models.ToDo.category_id == category_id)
    if priority is not None:
        query = query.filter(models.ToDo.priority == priority)
    if done is not None:
        query = query.filter(models.ToDo.done == done)
    
    # 默认排序：优先级降序→截止日期升序→创建时间降序
    if sort_by == "priority":
        query = query.order_by(desc(models.ToDo.priority), desc(models.ToDo.created_at))
    elif sort_by == "due_date":
        query = query.order_by(asc(models.ToDo.due_date), desc(models.ToDo.created_at))
    else:
        query = query.order_by(
            desc(models.ToDo.priority),
            asc(models.ToDo.due_date),
            desc(models.ToDo.created_at)
        )
    
    todos = query.all()
    
    # 按状态筛选
    if status:
        todos_with_status = add_todo_status(todos)
        todos = [t for t in todos if calculate_todo_status(t) == status]
    
    return todos


# 获取单个TODO
def get_todo(db: Session, todo_id: int, uid: int):
    todo = db.query(models.ToDo).filter(models.ToDo.id == todo_id, models.ToDo.owner_id == uid).first()
    if todo:
        setattr(todo, 'status', calculate_todo_status(todo))
    return todo


# 创建TODO信息
def create_todo(db: Session, todo_data: schemas_utils.ToDoCreate, owner_id: int):
    db_todo = models.ToDo(
        content=todo_data.content,
        done=todo_data.done,
        priority=todo_data.priority,
        due_date=todo_data.due_date,
        remind_before=todo_data.remind_before,
        category_id=todo_data.category_id,
        owner_id=owner_id
    )
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    return db_todo


# 删除TODO信息
def delete_todo(db: Session, todo_id: int, uid: int):
    res = db.query(models.ToDo).filter(models.ToDo.id == todo_id, models.ToDo.owner_id == uid).delete()
    db.commit()
    return res


# 修改TODO信息
def update_todo(db: Session, todo_id: int, todo_data: schemas_utils.ToDoUpdate, uid: int):
    db_todo = get_todo(db, todo_id, uid)
    if not db_todo:
        return None
    
    update_data = todo_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_todo, key, value)
    
    db.commit()
    db.refresh(db_todo)
    return db_todo


'''
# 统计分析
'''


# 获取基本统计数据
def get_todo_stats(db: Session, uid: int):
    now = datetime.utcnow()
    
    # 总数、已完成、未完成
    total = db.query(models.ToDo).filter(models.ToDo.owner_id == uid).count()
    completed = db.query(models.ToDo).filter(models.ToDo.owner_id == uid, models.ToDo.done == True).count()
    pending = total - completed
    completion_rate = round(completed / total * 100, 2) if total > 0 else 0
    
    # 已过期和即将过期
    overdue = db.query(models.ToDo).filter(
        models.ToDo.owner_id == uid,
        models.ToDo.done == False,
        models.ToDo.due_date < now
    ).count()
    
    # 即将过期（提醒时间内）
    upcoming = db.query(models.ToDo).filter(
        models.ToDo.owner_id == uid,
        models.ToDo.done == False,
        models.ToDo.due_date >= now
    ).count()
    
    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "completion_rate": completion_rate,
        "overdue": overdue,
        "upcoming": upcoming
    }


# 按分类统计
def get_stats_by_category(db: Session, uid: int):
    results = db.query(
        models.ToDo.category_id,
        models.Category.name.label("category_name"),
        func.count(models.ToDo.id).label("count")
    ).outerjoin(
        models.Category, models.ToDo.category_id == models.Category.id
    ).filter(
        models.ToDo.owner_id == uid
    ).group_by(
        models.ToDo.category_id, models.Category.name
    ).all()
    
    return [
        {
            "category_id": r.category_id or 0,
            "category_name": r.category_name or "无分类",
            "count": r.count
        } for r in results
    ]


# 按优先级统计
def get_stats_by_priority(db: Session, uid: int):
    results = db.query(
        models.ToDo.priority,
        func.count(models.ToDo.id).label("count")
    ).filter(
        models.ToDo.owner_id == uid
    ).group_by(
        models.ToDo.priority
    ).all()
    
    # 确保所有优先级都有数据
    priority_map = {1: 0, 2: 0, 3: 0}
    for r in results:
        priority_map[r.priority] = r.count
    
    return [
        {"priority": p, "count": c} for p, c in priority_map.items()
    ]


# 获取趋势数据
def get_trend_data(db: Session, uid: int, days: int):
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days - 1)
    
    results = db.query(
        func.date(models.ToDo.created_at).label("date"),
        func.count(models.ToDo.id).label("completed")
    ).filter(
        models.ToDo.owner_id == uid,
        models.ToDo.done == True,
        func.date(models.ToDo.created_at) >= start_date
    ).group_by(
        func.date(models.ToDo.created_at)
    ).all()
    
    # 转换为字典以便查找
    result_map = {str(r.date): r.completed for r in results}
    
    # 生成完整的日期序列
    trend = []
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        date_str = str(current_date)
        trend.append({
            "date": date_str,
            "completed": result_map.get(date_str, 0)
        })
    
    return trend


# 获取完整统计信息
def get_full_stats(db: Session, uid: int):
    return {
        "overview": get_todo_stats(db, uid),
        "by_category": get_stats_by_category(db, uid),
        "by_priority": get_stats_by_priority(db, uid),
        "trend_7days": get_trend_data(db, uid, 7),
        "trend_30days": get_trend_data(db, uid, 30)
    }


'''
# 提醒相关（用于定时任务）
'''


# 获取需要提醒的TODO
def get_todos_for_reminder(db: Session):
    now = datetime.utcnow()
    todos = db.query(models.ToDo).filter(
        models.ToDo.done == False,
        models.ToDo.is_reminded == False,
        models.ToDo.remind_before > 0,
        models.ToDo.due_date.isnot(None)
    ).all()
    
    need_remind = []
    for todo in todos:
        remind_time = todo.due_date - timedelta(minutes=todo.remind_before)
        if now >= remind_time:
            need_remind.append(todo)
    
    return need_remind


# 标记为已提醒
def mark_as_reminded(db: Session, todo_id: int):
    db.query(models.ToDo).filter(models.ToDo.id == todo_id).update({"is_reminded": True})
    db.commit()
