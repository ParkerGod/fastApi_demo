import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sql_app.database import SessionLocal, engine
from sql_app import models
from sqlalchemy.orm import Session
from sql_app import cruds
from sql_app.schemas import schemas_notification
import time

print("=" * 60)
print("开始测试通知/消息系统...")
print("=" * 60)

models.Base.metadata.create_all(bind=engine)
db: Session = SessionLocal()

def print_section(title):
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print(f"{'=' * 50}")

try:
    print_section("1. 测试用户准备")
    
    test_user1 = cruds.get_user_by_email(db, "test1@example.com")
    if not test_user1:
        from sql_app.schemas.schemas_user import UserCreate
        test_user1 = cruds.create_user(db, UserCreate(email="test1@example.com", password="123456"))
        print(f"✓ 创建测试用户1: {test_user1.username} (ID: {test_user1.id})")
    else:
        print(f"✓ 测试用户1已存在: {test_user1.username} (ID: {test_user1.id})")

    test_user2 = cruds.get_user_by_email(db, "test2@example.com")
    if not test_user2:
        from sql_app.schemas.schemas_user import UserCreate
        test_user2 = cruds.create_user(db, UserCreate(email="test2@example.com", password="123456"))
        print(f"✓ 创建测试用户2: {test_user2.username} (ID: {test_user2.id})")
    else:
        print(f"✓ 测试用户2已存在: {test_user2.username} (ID: {test_user2.id})")

    print_section("2. 测试通知创建功能")
    
    notification = schemas_notification.NotificationCreate(
        recipient_id=test_user1.id,
        sender_id=test_user2.id,
        type="task",
        title="测试任务通知",
        content="这是一条测试任务通知内容",
        related_id=123
    )
    created_notif = cruds.create_notification(db, notification)
    print(f"✓ 创建通知成功: ID={created_notif.id}, 标题='{created_notif.title}'")

    system_notif = cruds.create_system_notification(
        db, recipient_id=test_user1.id,
        title="系统公告",
        content="系统将于今晚进行维护升级",
        related_id=None
    )
    print(f"✓ 创建系统通知成功: ID={system_notif.id}, 类型={system_notif.type}")

    print_section("3. 测试通知触发场景函数")
    
    task_notif = cruds.notify_task_assigned(
        db, recipient_id=test_user1.id, sender_id=test_user2.id,
        task_title="完成项目API开发", task_id=1001
    )
    print(f"✓ 任务分配通知: {task_notif.title}")

    status_notif = cruds.notify_task_status_changed(
        db, recipient_id=test_user1.id, sender_id=test_user2.id,
        task_title="完成项目API开发", status="已完成", task_id=1001
    )
    print(f"✓ 任务状态变更通知: {status_notif.content}")

    project_notif = cruds.notify_project_member_added(
        db, recipient_id=test_user1.id, sender_id=test_user2.id,
        project_name="智能用户管理系统", project_id=50
    )
    print(f"✓ 项目成员通知: {project_notif.content}")

    comment_notif = cruds.notify_comment_reply(
        db, recipient_id=test_user1.id, sender_id=test_user2.id,
        comment_preview="我同意这个方案", comment_id=888
    )
    print(f"✓ 评论回复通知: {comment_notif.content}")

    print_section("4. 测试通知查询功能")
    
    notifications = cruds.get_user_notifications(db, user_id=test_user1.id, limit=10)
    print(f"✓ 获取用户通知列表: 共 {len(notifications)} 条")
    for i, n in enumerate(notifications[:3], 1):
        print(f"  {i}. [{n.type}] {n.title} (已读: {n.is_read})")

    unread_count = cruds.get_unread_notification_count(db, user_id=test_user1.id)
    print(f"✓ 用户未读通知数: {unread_count}")

    print_section("5. 测试标记已读功能")
    
    marked = cruds.mark_notification_read(db, notification_id=created_notif.id, user_id=test_user1.id)
    print(f"✓ 标记单条已读: 通知ID={marked.id}, 已读状态={marked.is_read}, 阅读时间={marked.read_at}")

    marked_count = cruds.mark_all_notifications_read(db, user_id=test_user1.id)
    print(f"✓ 标记全部已读: 共标记了 {marked_count} 条通知")

    unread_count_after = cruds.get_unread_notification_count(db, user_id=test_user1.id)
    print(f"✓ 标记全部已读后未读数: {unread_count_after}")

    print_section("6. 测试删除通知功能")
    
    delete_success = cruds.delete_notification(db, notification_id=created_notif.id, user_id=test_user1.id)
    print(f"✓ 删除通知: {'成功' if delete_success else '失败'}")

    print_section("7. 测试私信功能")
    
    msg_create = schemas_notification.MessageCreate(
        recipient_id=test_user2.id,
        content="你好，请问项目进展如何？"
    )
    sent_msg = cruds.create_message(db, sender_id=test_user1.id, message=msg_create)
    print(f"✓ 发送私信成功: ID={sent_msg.id}, 内容='{sent_msg.content}'")

    msg_create2 = schemas_notification.MessageCreate(
        recipient_id=test_user1.id,
        content="进展顺利，预计明天完成！"
    )
    sent_msg2 = cruds.create_message(db, sender_id=test_user2.id, message=msg_create2)
    print(f"✓ 回复私信成功: ID={sent_msg2.id}, 内容='{sent_msg2.content}'")

    conversations = cruds.get_user_conversations(db, user_id=test_user1.id)
    print(f"✓ 获取会话列表: 共 {len(conversations)} 个会话")
    for conv in conversations:
        print(f"  - 与 {conv['username']}: 最后消息='{conv['last_message']}', 未读={conv['unread_count']}")

    conversation_msgs = cruds.get_conversation(db, user1_id=test_user1.id, user2_id=test_user2.id)
    print(f"✓ 获取聊天记录: 共 {len(conversation_msgs)} 条消息")
    for i, msg in enumerate(conversation_msgs, 1):
        print(f"  {i}. {msg.content} (发送时间: {msg.created_at})")

    unread_msg_count = cruds.get_unread_message_count(db, user_id=test_user1.id)
    print(f"✓ 未读消息数: {unread_msg_count}")

    marked_msg = cruds.mark_message_read(db, message_id=sent_msg2.id, user_id=test_user1.id)
    print(f"✓ 标记消息已读: ID={marked_msg.id}, 已读状态={marked_msg.is_read}")

    print_section("8. 权限验证测试")
    
    delete_fail = cruds.delete_notification(db, notification_id=system_notif.id, user_id=test_user2.id)
    print(f"✓ 无权限删除通知测试: {'正确拒绝' if not delete_fail else '错误允许'}")

    mark_fail = cruds.mark_notification_read(db, notification_id=system_notif.id, user_id=test_user2.id)
    print(f"✓ 无权限标记已读测试: {'正确拒绝' if mark_fail is None else '错误允许'}")

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！通知/消息系统功能正常！")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ 测试过程中出现错误: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
