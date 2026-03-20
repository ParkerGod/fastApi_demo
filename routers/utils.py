from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sql_app.database import get_db
from routers.auth import role_check
from sql_app.schemas import schemas_utils, schemas_user
from sql_app import cruds

router = APIRouter()


@router.post("/api/category/", response_model=schemas_utils.Category)
async def create_category(
    category_data: schemas_utils.CategoryCreate,
    db: Session = Depends(get_db),
    role_res: schemas_user.User = Depends(role_check)
):
    if role_res.id != category_data.owner_id:
        raise HTTPException(status_code=403, detail="Permission denied")
    return cruds.create_category(db=db, category_data=category_data)


@router.get("/api/category/", response_model=List[schemas_utils.Category])
async def get_categories(
    db: Session = Depends(get_db),
    role_res: schemas_user.User = Depends(role_check)
):
    return cruds.get_categories(db, owner_id=role_res.id)


@router.put("/api/category/{category_id}", response_model=schemas_utils.Category)
async def update_category(
    category_id: int,
    category_data: schemas_utils.CategoryUpdate,
    db: Session = Depends(get_db),
    role_res: schemas_user.User = Depends(role_check)
):
    category = cruds.update_category(db, category_id, role_res.id, category_data)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.delete("/api/category/{category_id}")
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    role_res: schemas_user.User = Depends(role_check)
):
    res = cruds.delete_category(db, category_id, role_res.id)
    if res <= 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"msg": "Successfully deleted {} data".format(res)}


@router.post("/api/todo/", response_model=schemas_utils.ToDoResponse)
async def create_todo(
    todo_data: schemas_utils.ToDoCreate,
    db: Session = Depends(get_db),
    role_res: schemas_user.User = Depends(role_check)
):
    if role_res.id != todo_data.owner_id:
        raise HTTPException(status_code=403, detail="Permission denied")
    if todo_data.category_id:
        category = cruds.get_category(db, todo_data.category_id, role_res.id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
    return cruds.create_todo(db=db, todo_data=todo_data)


@router.get("/api/todo/", response_model=List[schemas_utils.ToDoWithStatus])
async def get_todos(
    category_id: Optional[int] = Query(None),
    priority: Optional[int] = Query(None, ge=1, le=3),
    include_done: bool = Query(True),
    db: Session = Depends(get_db),
    role_res: schemas_user.User = Depends(role_check)
):
    todos = cruds.get_todo(
        db, uid=role_res.id,
        category_id=category_id,
        priority=priority,
        include_done=include_done
    )
    result = []
    for todo in todos:
        todo_dict = {
            "id": todo.id,
            "content": todo.content,
            "done": todo.done,
            "owner_id": todo.owner_id,
            "category_id": todo.category_id,
            "priority": todo.priority,
            "due_date": todo.due_date,
            "remind_before": todo.remind_before,
            "is_reminded": todo.is_reminded,
            "created_at": todo.created_at,
            "status": cruds.get_todo_status(todo.due_date, todo.done)
        }
        result.append(todo_dict)
    return result


@router.get("/api/todo/{todo_id}", response_model=schemas_utils.ToDoWithStatus)
async def get_todo_by_id(
    todo_id: int,
    db: Session = Depends(get_db),
    role_res: schemas_user.User = Depends(role_check)
):
    todo = cruds.get_todo_by_id(db, todo_id, role_res.id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    todo_dict = {
        "id": todo.id,
        "content": todo.content,
        "done": todo.done,
        "owner_id": todo.owner_id,
        "category_id": todo.category_id,
        "priority": todo.priority,
        "due_date": todo.due_date,
        "remind_before": todo.remind_before,
        "is_reminded": todo.is_reminded,
        "created_at": todo.created_at,
        "status": cruds.get_todo_status(todo.due_date, todo.done)
    }
    return todo_dict


@router.put("/api/todo/{todo_id}", response_model=schemas_utils.ToDoResponse)
async def update_todo(
    todo_id: int,
    todo_data: schemas_utils.ToDoUpdate,
    db: Session = Depends(get_db),
    role_res: schemas_user.User = Depends(role_check)
):
    if todo_data.category_id:
        category = cruds.get_category(db, todo_data.category_id, role_res.id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
    
    todo = cruds.update_todo(db, todo_id, role_res.id, todo_data)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.delete("/api/todo/{todo_id}")
async def delete_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    role_res: schemas_user.User = Depends(role_check)
):
    res = cruds.delete_todo(db, todo_id, role_res.id)
    if res <= 0:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"msg": "Successfully deleted {} data".format(res)}


@router.get("/api/statistics/", response_model=schemas_utils.StatisticsResponse)
async def get_statistics(
    db: Session = Depends(get_db),
    role_res: schemas_user.User = Depends(role_check)
):
    return cruds.get_statistics(db, owner_id=role_res.id)
