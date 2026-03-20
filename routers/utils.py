from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sql_app import cruds
from sqlalchemy.orm import Session
from sql_app.database import get_db
from routers.auth import role_check
from sql_app.schemas import schemas_utils, schemas_user

router = APIRouter()


# ==================== TODO 路由 ====================

@router.post("/api/todo/", response_model=schemas_utils.ToDo)
async def create_todo(
    todo_data: schemas_utils.ToDoCreate,
    db: Session = Depends(get_db),
    role_res: schemas_user.User = Depends(role_check)
):
    """创建TODO"""
    # 验证分类是否存在且属于当前用户
    if todo_data.category_id:
        category = cruds.get_category_by_id(db, todo_data.category_id, role_res.id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
    return cruds.create_todo(db=db, todo_data=todo_data, uid=role_res.id)


@router.get("/api/todo/", response_model=List[schemas_utils.ToDoWithStatus])
async def get_todos(
    category_id: Optional[int] = Query(None, description="按分类筛选"),
    priority: Optional[int] = Query(None, ge=1, le=3, description="按优先级筛选 (1=低, 2=中, 3=高)"),
    done: Optional[bool] = Query(None, description="按完成状态筛选"),
    status: Optional[str] = Query(None, description="按状态筛选 (overdue=已过期, upcoming=即将过期, normal=正常)"),
    db: Session = Depends(get_db),
    role_res: schemas_user.User = Depends(role_check)
):
    """获取TODO列表，支持多种筛选条件，返回包含status字段"""
    filters = schemas_utils.ToDoFilter(
        category_id=category_id,
        priority=priority,
        done=done,
        status=status
    )
    return cruds.get_todo_with_status(db, uid=role_res.id, filters=filters)


@router.get("/api/todo/{todo_id}", response_model=schemas_utils.ToDo)
async def get_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    role_res: schemas_user.User = Depends(role_check)
):
    """根据ID获取单个TODO"""
    todo = cruds.get_todo_by_id(db, todo_id=todo_id, uid=role_res.id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.put("/api/todo/{todo_id}", response_model=schemas_utils.ToDo)
async def update_todo(
    todo_id: int,
    todo_data: schemas_utils.ToDoUpdate,
    db: Session = Depends(get_db),
    role_res: schemas_user.User = Depends(role_check)
):
    """更新TODO信息"""
    # 验证分类是否存在
    if todo_data.category_id:
        category = cruds.get_category_by_id(db, todo_data.category_id, role_res.id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

    # 如果修改了截止日期，重置提醒状态
    existing_todo = cruds.get_todo_by_id(db, todo_id, role_res.id)
    if not existing_todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    if todo_data.due_date and todo_data.due_date != existing_todo.due_date:
        cruds.reset_reminder(db, todo_id, role_res.id)

    updated_todo = cruds.update_todo(db, todo_id=todo_id, todo_data=todo_data, uid=role_res.id)
    if not updated_todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return updated_todo


@router.delete("/api/todo/{todo_id}")
async def delete_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    role_res: schemas_user.User = Depends(role_check)
):
    """删除TODO"""
    res = cruds.delete_todo(db, todo_id=todo_id, uid=role_res.id)
    if res <= 0:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"detail": f"Successfully deleted {res} data"}


# ==================== Category 路由 ====================

@router.post("/api/category/", response_model=schemas_utils.Category)
async def create_category(
    category_data: schemas_utils.CategoryCreate,
    db: Session = Depends(get_db),
    role_res: schemas_user.User = Depends(role_check)
):
    """创建分类"""
    if role_res.id != category_data.owner_id:
        raise HTTPException(status_code=403, detail="Permission denied")
    return cruds.create_category(db=db, category_data=category_data)


@router.get("/api/category/", response_model=List[schemas_utils.CategoryWithTodoCount])
async def get_categories(
    db: Session = Depends(get_db),
    role_res: schemas_user.User = Depends(role_check)
):
    """获取用户的所有分类及其TODO数量"""
    categories = cruds.get_category_with_todo_count(db, uid=role_res.id)
    result = []
    for category, todo_count in categories:
        category_dict = {
            "id": category.id,
            "name": category.name,
            "color": category.color,
            "icon": category.icon,
            "sort_order": category.sort_order,
            "owner_id": category.owner_id,
            "todo_count": todo_count
        }
        result.append(schemas_utils.CategoryWithTodoCount(**category_dict))
    return result


@router.get("/api/category/{category_id}", response_model=schemas_utils.Category)
async def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    role_res: schemas_user.User = Depends(role_check)
):
    """根据ID获取分类"""
    category = cruds.get_category_by_id(db, category_id=category_id, uid=role_res.id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.put("/api/category/{category_id}", response_model=schemas_utils.Category)
async def update_category(
    category_id: int,
    category_data: schemas_utils.CategoryUpdate,
    db: Session = Depends(get_db),
    role_res: schemas_user.User = Depends(role_check)
):
    """更新分类"""
    updated_category = cruds.update_category(
        db, category_id=category_id, category_data=category_data, uid=role_res.id
    )
    if not updated_category:
        raise HTTPException(status_code=404, detail="Category not found")
    return updated_category


@router.delete("/api/category/{category_id}")
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    role_res: schemas_user.User = Depends(role_check)
):
    """删除分类，该分类下的TODO将变为未分类"""
    res = cruds.delete_category(db, category_id=category_id, uid=role_res.id)
    if res <= 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"detail": f"Successfully deleted {res} data"}


# ==================== Statistics 路由 ====================

@router.get("/api/statistics/", response_model=schemas_utils.TodoStatistics)
async def get_statistics(
    db: Session = Depends(get_db),
    role_res: schemas_user.User = Depends(role_check)
):
    """获取TODO统计信息"""
    return cruds.get_todo_statistics(db, uid=role_res.id)


@router.get("/api/todos/overdue/", response_model=List[schemas_utils.ToDo])
async def get_overdue_todos(
    db: Session = Depends(get_db),
    role_res: schemas_user.User = Depends(role_check)
):
    """获取已过期的TODO列表"""
    filters = schemas_utils.ToDoFilter(status="overdue")
    return cruds.get_todo(db, uid=role_res.id, filters=filters)


@router.get("/api/todos/upcoming/", response_model=List[schemas_utils.ToDo])
async def get_upcoming_todos(
    hours: int = Query(24, ge=1, le=168, description="未来几小时内到期"),
    db: Session = Depends(get_db),
    role_res: schemas_user.User = Depends(role_check)
):
    """获取即将到期的TODO列表（默认24小时内）"""
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    upcoming_time = now + timedelta(hours=hours)

    todos = cruds.get_todo(db, uid=role_res.id, filters=schemas_utils.ToDoFilter(done=False))

    # 筛选即将到期的
    upcoming_todos = []
    for todo in todos:
        if todo.due_date and now <= todo.due_date <= upcoming_time:
            upcoming_todos.append(todo)

    return upcoming_todos
