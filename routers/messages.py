from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sql_app import cruds
from sql_app.database import get_db
from sql_app.schemas import schemas_notification, schemas_user
from routers.auth import get_current_active_user

router = APIRouter()


@router.get("/api/messages/", response_model=List[schemas_notification.ConversationItem])
async def get_conversations(
    db: Session = Depends(get_db),
    current_user: schemas_user.User = Depends(get_current_active_user)
):
    conversations = cruds.get_user_conversations(db, user_id=current_user.id)
    return conversations


@router.get("/api/messages/conversation/{user_id}", response_model=List[schemas_notification.Message])
async def get_conversation_messages(
    user_id: int,
    skip: int = 0,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: schemas_user.User = Depends(get_current_active_user)
):
    messages = cruds.get_conversation(db, user1_id=current_user.id, user2_id=user_id, skip=skip, limit=limit)
    return messages


@router.post("/api/messages/", response_model=schemas_notification.Message)
async def send_message(
    message: schemas_notification.MessageCreate,
    db: Session = Depends(get_db),
    current_user: schemas_user.User = Depends(get_current_active_user)
):
    if current_user.id == message.recipient_id:
        raise HTTPException(status_code=400, detail="Cannot send message to yourself")
    recipient = cruds.get_user(db, user_id=message.recipient_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    db_message = cruds.create_message(db, sender_id=current_user.id, message=message)
    return db_message


@router.get("/api/messages/unread-count")
async def get_unread_message_count(
    db: Session = Depends(get_db),
    current_user: schemas_user.User = Depends(get_current_active_user)
):
    count = cruds.get_unread_message_count(db, user_id=current_user.id)
    return {"unread_count": count}


@router.put("/api/messages/{id}/read", response_model=schemas_notification.Message)
async def mark_message_read(
    id: int,
    db: Session = Depends(get_db),
    current_user: schemas_user.User = Depends(get_current_active_user)
):
    message = cruds.mark_message_read(db, message_id=id, user_id=current_user.id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found or permission denied")
    return message
