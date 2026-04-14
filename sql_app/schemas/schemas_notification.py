from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class NotificationBase(BaseModel):
    recipient_id: int
    sender_id: Optional[int] = None
    type: str
    title: str
    content: str
    related_id: Optional[int] = None


class NotificationCreate(NotificationBase):
    pass


class Notification(NotificationBase):
    id: int
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class MessageBase(BaseModel):
    recipient_id: int
    content: str


class MessageCreate(MessageBase):
    pass


class Message(MessageBase):
    id: int
    sender_id: int
    is_read: bool
    created_at: datetime

    class Config:
        orm_mode = True


class ConversationItem(BaseModel):
    user_id: int
    username: str
    avatar: Optional[str] = None
    last_message: str
    last_message_time: datetime
    unread_count: int
