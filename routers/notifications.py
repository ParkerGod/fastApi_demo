from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sql_app import cruds
from sql_app.database import get_db
from sql_app.schemas import schemas_notification, schemas_user
from routers.auth import get_current_active_user

router = APIRouter()


@router.get("/api/notifications/", response_model=List[schemas_notification.Notification])
async def get_notifications(
    skip: int = 0,
    limit: int = Query(50, ge=1, le=200),
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: schemas_user.User = Depends(get_current_active_user)
):
    notifications = cruds.get_user_notifications(db, user_id=current_user.id, skip=skip, limit=limit, unread_only=unread_only)
    return notifications


@router.get("/api/notifications/unread-count")
async def get_unread_notification_count(
    db: Session = Depends(get_db),
    current_user: schemas_user.User = Depends(get_current_active_user)
):
    count = cruds.get_unread_notification_count(db, user_id=current_user.id)
    return {"unread_count": count}


@router.put("/api/notifications/{id}/read", response_model=schemas_notification.Notification)
async def mark_notification_read(
    id: int,
    db: Session = Depends(get_db),
    current_user: schemas_user.User = Depends(get_current_active_user)
):
    notification = cruds.mark_notification_read(db, notification_id=id, user_id=current_user.id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found or permission denied")
    return notification


@router.put("/api/notifications/read-all")
async def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: schemas_user.User = Depends(get_current_active_user)
):
    count = cruds.mark_all_notifications_read(db, user_id=current_user.id)
    return {"msg": f"Successfully marked {count} notifications as read"}


@router.delete("/api/notifications/{id}")
async def delete_notification(
    id: int,
    db: Session = Depends(get_db),
    current_user: schemas_user.User = Depends(get_current_active_user)
):
    success = cruds.delete_notification(db, notification_id=id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found or permission denied")
    return {"msg": "Notification deleted successfully"}
