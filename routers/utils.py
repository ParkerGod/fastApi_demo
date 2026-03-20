from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sql_app import cruds
from sqlalchemy.orm import Session
from sql_app.database import get_db
from routers.auth import role_check
from sql_app.schemas import schemas_utils, schemas_user

router = APIRouter()
'''
# 分类管理
'''


# 新增分类
@router.post("/api/categories/", response_model=schemas_utils.Category)
async def create_category(
    category_data: schemas_utils.CategoryCreate,
    db: Session = Depends(get_db),
    current_user: schemas_user.User = Depends(role_check)
):
    return cruds.create_category(db=db, category_data=category_data, owner_id=current_user.id)


# 获取所有分类
@router.get("/api/categories/", response_model=List[schemas_utils.Category])
async def get_categories(
    db: Session = Depends(get_db),
    current_user: schemas_user.User = Depends(role_check)
):
    return cruds.get_categories(db=db, owner_id=current_user.id)


# 获取单个分类
@router.get("/api/categories/{category_id}", response_model=schemas_utils.Category)
async def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: schemas_user.User = Depends(role_check)
):
    db_category = cruds.get_category(db, category_id=category_id, owner_id=current_user.id)
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return db_category


# 更新分类
@router.put("/api/categories/{category_id}", response_model=schemas_utils.Category)
async def update_category(
    category_id: int,
    category_data: schemas_utils.CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: schemas_user.User = Depends(role_check)
):
    db_category = cruds.update_category(db, category_id=category_id, category_data=category_data, owner_id=current_user.id)
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return db_category


# 删除分类
@router.delete("/api/categories/{category_id}")
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: schemas_user.User = Depends(role_check)
):
    res = cruds.delete_category(db, category_id=category_id, owner_id=current_user.id)
    if res <= 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"msg": "Successfully deleted {} category".format(res)}


'''
# TODO管理
'''


# 新增TODO
@router.post("/api/todo/", response_model=schemas_utils.ToDo)
async def create_todo(
    todo_data: schemas_utils.ToDoCreate,
    db: Session = Depends(get_db),
    current_user: schemas_user.User = Depends(role_check)
):
    # 验证优先级范围
    if todo_data.priority and todo_data.priority not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Priority must be 1 (low), 2 (medium), or 3 (high)")
    
    # 验证分类是否存在（如果指定了分类）
    if todo_data.category_id:
        db_category = cruds.get_category(db, category_id=todo_data.category_id, owner_id=current_user.id)
        if db_category is None:
            raise HTTPException(status_code=404, detail="Category not found")
    
    return cruds.create_todo(db=db, todo_data=todo_data, owner_id=current_user.id)


# 获取TODO列表（支持筛选和排序）
@router.get("/api/todo/", response_model=List[schemas_utils.ToDo])
async def get_todos(
    category_id: Optional[int] = Query(None, description="按分类ID筛选"),
    priority: Optional[int] = Query(None, description="按优先级筛选 (1=低, 2=中, 3=高)"),
    done: Optional[bool] = Query(None, description="按完成状态筛选"),
    status: Optional[str] = Query(None, description="按状态筛选 (overdue/upcoming/normal)"),
    sort_by: Optional[str] = Query(None, description="排序方式 (priority/due_date)"),
    db: Session = Depends(get_db),
    current_user: schemas_user.User = Depends(role_check)
):
    # 验证参数
    if priority and priority not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Priority must be 1 (low), 2 (medium), or 3 (high)")
    if status and status not in ["overdue", "upcoming", "normal"]:
        raise HTTPException(status_code=400, detail="Status must be overdue, upcoming, or normal")
    if sort_by and sort_by not in ["priority", "due_date"]:
        raise HTTPException(status_code=400, detail="Sort_by must be priority or due_date")
    
    todos = cruds.get_todos(
        db,
        uid=current_user.id,
        category_id=category_id,
        priority=priority,
        done=done,
        status=status,
        sort_by=sort_by
    )
    
    # 添加状态信息
    todos_with_status = []
    for todo in todos:
        todo.status = cruds.calculate_todo_status(todo)
        todos_with_status.append(todo)
    
    return todos_with_status


# 获取单个TODO
@router.get("/api/todo/{todo_id}", response_model=schemas_utils.ToDo)
async def get_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: schemas_user.User = Depends(role_check)
):
    db_todo = cruds.get_todo(db, todo_id=todo_id, uid=current_user.id)
    if db_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return db_todo


# 删除TODO
@router.delete("/api/todo/{todo_id}")
async def delete_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: schemas_user.User = Depends(role_check)
):
    res = cruds.delete_todo(db, todo_id=todo_id, uid=current_user.id)
    if res <= 0:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"msg": "Successfully deleted {} data".format(res)}


# 更新TODO
@router.put("/api/todo/{todo_id}", response_model=schemas_utils.ToDo)
async def update_todo(
    todo_id: int,
    todo_data: schemas_utils.ToDoUpdate,
    db: Session = Depends(get_db),
    current_user: schemas_user.User = Depends(role_check)
):
    # 验证优先级范围
    if todo_data.priority and todo_data.priority not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Priority must be 1 (low), 2 (medium), or 3 (high)")
    
    # 验证分类是否存在（如果指定了分类）
    if todo_data.category_id:
        db_category = cruds.get_category(db, category_id=todo_data.category_id, owner_id=current_user.id)
        if db_category is None:
            raise HTTPException(status_code=404, detail="Category not found")
    
    db_todo = cruds.update_todo(db, todo_id=todo_id, todo_data=todo_data, uid=current_user.id)
    if db_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return db_todo


'''
# 统计分析
'''


# 获取统计信息
@router.get("/api/stats/todo", response_model=schemas_utils.StatsResponse)
async def get_todo_stats(
    db: Session = Depends(get_db),
    current_user: schemas_user.User = Depends(role_check)
):
    return cruds.get_full_stats(db, uid=current_user.id)


'''
# 提醒相关（测试接口）
'''


# 手动触发提醒检查（用于测试）
@router.post("/api/reminders/check")
async def check_reminders(
    db: Session = Depends(get_db),
    current_user: schemas_user.User = Depends(role_check)
):
    # 这里简化为只检查当前用户的提醒
    from sqlalchemy import and_
    from datetime import datetime, timedelta
    
    now = datetime.utcnow()
    todos = db.query(cruds.models.ToDo).filter(
        cruds.models.ToDo.owner_id == current_user.id,
        cruds.models.ToDo.done == False,
        cruds.models.ToDo.is_reminded == False,
        cruds.models.ToDo.remind_before > 0,
        cruds.models.ToDo.due_date.isnot(None)
    ).all()
    
    need_remind = []
    for todo in todos:
        remind_time = todo.due_date - timedelta(minutes=todo.remind_before)
        if now >= remind_time:
            need_remind.append({
                "id": todo.id,
                "content": todo.content,
                "due_date": todo.due_date,
                "remind_before": todo.remind_before
            })
            cruds.mark_as_reminded(db, todo.id)
    
    return {
        "reminders": need_remind,
        "count": len(need_remind)
    }
