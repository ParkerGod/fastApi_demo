from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, func
from datetime import datetime
from .. import models
from ..schemas import schemas_notification


def create_notification(db: Session, notification: schemas_notification.NotificationCreate):
    db_notification = models.Notification(
        recipient_id=notification.recipient_id,
        sender_id=notification.sender_id,
        type=notification.type,
        title=notification.title,
        content=notification.content,
        related_id=notification.related_id
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification


def create_system_notification(db: Session, recipient_id: int, title: str, content: str, related_id: int = None):
    notification = schemas_notification.NotificationCreate(
        recipient_id=recipient_id,
        sender_id=None,
        type="system",
        title=title,
        content=content,
        related_id=related_id
    )
    return create_notification(db, notification)


def get_user_notifications(db: Session, user_id: int, skip: int = 0, limit: int = 50, unread_only: bool = False):
    query = db.query(models.Notification).filter(models.Notification.recipient_id == user_id)
    if unread_only:
        query = query.filter(models.Notification.is_read == False)
    return query.order_by(desc(models.Notification.created_at)).offset(skip).limit(limit).all()


def get_unread_notification_count(db: Session, user_id: int):
    return db.query(models.Notification).filter(
        models.Notification.recipient_id == user_id,
        models.Notification.is_read == False
    ).count()


def get_notification_by_id(db: Session, notification_id: int):
    return db.query(models.Notification).filter(models.Notification.id == notification_id).first()


def mark_notification_read(db: Session, notification_id: int, user_id: int):
    notification = get_notification_by_id(db, notification_id)
    if not notification or notification.recipient_id != user_id:
        return None
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.commit()
    return notification


def mark_all_notifications_read(db: Session, user_id: int):
    count = db.query(models.Notification).filter(
        models.Notification.recipient_id == user_id,
        models.Notification.is_read == False
    ).update({
        models.Notification.is_read: True,
        models.Notification.read_at: datetime.utcnow()
    })
    db.commit()
    return count


def delete_notification(db: Session, notification_id: int, user_id: int):
    notification = get_notification_by_id(db, notification_id)
    if not notification or notification.recipient_id != user_id:
        return False
    db.delete(notification)
    db.commit()
    return True


def create_message(db: Session, sender_id: int, message: schemas_notification.MessageCreate):
    db_message = models.Message(
        sender_id=sender_id,
        recipient_id=message.recipient_id,
        content=message.content
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message


def get_conversation(db: Session, user1_id: int, user2_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Message).filter(
        or_(
            and_(models.Message.sender_id == user1_id, models.Message.recipient_id == user2_id),
            and_(models.Message.sender_id == user2_id, models.Message.recipient_id == user1_id)
        )
    ).order_by(desc(models.Message.created_at)).offset(skip).limit(limit).all()


def get_user_conversations(db: Session, user_id: int):
    all_messages = db.query(models.Message).filter(
        or_(models.Message.sender_id == user_id, models.Message.recipient_id == user_id)
    ).order_by(desc(models.Message.created_at)).all()
    
    last_messages = {}
    for msg in all_messages:
        other_user_id = msg.recipient_id if msg.sender_id == user_id else msg.sender_id
        if other_user_id not in last_messages:
            last_messages[other_user_id] = msg
    
    conversations = []
    for other_user_id, msg in last_messages.items():
        other_user = db.query(models.User).filter(models.User.id == other_user_id).first()
        unread_count = db.query(models.Message).filter(
            models.Message.sender_id == other_user_id,
            models.Message.recipient_id == user_id,
            models.Message.is_read == False
        ).count()
        conversations.append({
            'user_id': other_user_id,
            'username': other_user.username if other_user else 'Unknown',
            'avatar': other_user.avatar if other_user else None,
            'last_message': msg.content,
            'last_message_time': msg.created_at,
            'unread_count': unread_count
        })
    
    conversations.sort(key=lambda x: x['last_message_time'], reverse=True)
    return conversations


def get_unread_message_count(db: Session, user_id: int):
    return db.query(models.Message).filter(
        models.Message.recipient_id == user_id,
        models.Message.is_read == False
    ).count()


def get_message_by_id(db: Session, message_id: int):
    return db.query(models.Message).filter(models.Message.id == message_id).first()


def mark_message_read(db: Session, message_id: int, user_id: int):
    message = get_message_by_id(db, message_id)
    if not message or message.recipient_id != user_id:
        return None
    message.is_read = True
    db.commit()
    return message


def notify_task_assigned(db: Session, recipient_id: int, sender_id: int, task_title: str, task_id: int):
    notification = schemas_notification.NotificationCreate(
        recipient_id=recipient_id,
        sender_id=sender_id,
        type="task",
        title="任务已分配",
        content=f"您已被分配了新任务: {task_title}",
        related_id=task_id
    )
    return create_notification(db, notification)


def notify_task_status_changed(db: Session, recipient_id: int, sender_id: int, task_title: str, status: str, task_id: int):
    notification = schemas_notification.NotificationCreate(
        recipient_id=recipient_id,
        sender_id=sender_id,
        type="task",
        title="任务状态变更",
        content=f"任务 '{task_title}' 状态已更新为: {status}",
        related_id=task_id
    )
    return create_notification(db, notification)


def notify_project_member_added(db: Session, recipient_id: int, sender_id: int, project_name: str, project_id: int):
    notification = schemas_notification.NotificationCreate(
        recipient_id=recipient_id,
        sender_id=sender_id,
        type="project",
        title="项目成员更新",
        content=f"您已被加入项目: {project_name}",
        related_id=project_id
    )
    return create_notification(db, notification)


def notify_comment_reply(db: Session, recipient_id: int, sender_id: int, comment_preview: str, comment_id: int):
    sender = db.query(models.User).filter(models.User.id == sender_id).first()
    sender_name = sender.username if sender else 'Someone'
    notification = schemas_notification.NotificationCreate(
        recipient_id=recipient_id,
        sender_id=sender_id,
        type="comment",
        title="收到回复",
        content=f"{sender_name} 回复了您: {comment_preview}",
        related_id=comment_id
    )
    return create_notification(db, notification)
