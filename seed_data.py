#!/usr/bin/env python
# coding=utf-8
"""
测试数据创建脚本
用于创建测试用的分类、TODO数据
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sql_app.database import SessionLocal, engine
from sql_app import models
import bcrypt


SECRET_KEY = "wangcheng"


def get_password_hash(password: str) -> str:
    # 使用 bcrypt 直接处理，确保编码正确
    password_with_secret = password + SECRET_KEY
    password_bytes = password_with_secret.encode('utf-8')[:72]  # bcrypt 限制 72 字节
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def create_test_data():
    # 先创建所有表
    models.Base.metadata.create_all(bind=engine)
    """创建测试数据"""
    db = SessionLocal()
    try:
        # 检查是否已有用户
        existing_user = db.query(models.User).filter(models.User.email == "test@example.com").first()
        if existing_user:
            print("测试用户已存在，跳过创建")
            user = existing_user
        else:
            # 创建测试用户
            user = models.User(
                email="test@example.com",
                username="测试用户",
                hashed_password=get_password_hash("password123"),
                role="general",
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"创建测试用户: {user.email} (ID: {user.id})")

        # 创建分类
        categories_data = [
            {"name": "工作", "color": "#3B82F6", "icon": "briefcase", "sort_order": 1},
            {"name": "学习", "color": "#10B981", "icon": "book", "sort_order": 2},
            {"name": "生活", "color": "#F59E0B", "icon": "home", "sort_order": 3},
            {"name": "健康", "color": "#EF4444", "icon": "heart", "sort_order": 4},
            {"name": "娱乐", "color": "#8B5CF6", "icon": "gamepad", "sort_order": 5},
        ]

        categories = {}
        for cat_data in categories_data:
            existing = db.query(models.Category).filter(
                models.Category.name == cat_data["name"],
                models.Category.owner_id == user.id
            ).first()

            if existing:
                categories[cat_data["name"]] = existing
                print(f"分类 '{cat_data['name']}' 已存在")
            else:
                category = models.Category(
                    name=cat_data["name"],
                    color=cat_data["color"],
                    icon=cat_data["icon"],
                    sort_order=cat_data["sort_order"],
                    owner_id=user.id
                )
                db.add(category)
                db.commit()
                db.refresh(category)
                categories[cat_data["name"]] = category
                print(f"创建分类: {category.name}")

        # 创建TODO数据
        now = datetime.utcnow()

        todos_data = [
            # 高优先级 - 即将过期（用于测试提醒功能）
            {
                "content": "完成项目报告",
                "done": False,
                "category_id": categories["工作"].id,
                "priority": 3,
                "due_date": now + timedelta(minutes=20),  # 20分钟后到期
                "remind_before": 30,
                "is_reminded": False
            },
            {
                "content": "准备会议材料",
                "done": False,
                "category_id": categories["工作"].id,
                "priority": 3,
                "due_date": now + timedelta(hours=2),
                "remind_before": 30,
                "is_reminded": False
            },
            # 中优先级
            {
                "content": "学习FastAPI文档",
                "done": False,
                "category_id": categories["学习"].id,
                "priority": 2,
                "due_date": now + timedelta(days=1),
                "remind_before": 60,
                "is_reminded": False
            },
            {
                "content": "阅读技术博客",
                "done": True,
                "category_id": categories["学习"].id,
                "priority": 2,
                "due_date": now - timedelta(days=1),
                "remind_before": 30,
                "is_reminded": False,
                "completed_at": now - timedelta(hours=2)
            },
            # 低优先级
            {
                "content": "买 groceries",
                "done": False,
                "category_id": categories["生活"].id,
                "priority": 1,
                "due_date": now + timedelta(days=3),
                "remind_before": 120,
                "is_reminded": False
            },
            {
                "content": "整理房间",
                "done": False,
                "category_id": categories["生活"].id,
                "priority": 1,
                "due_date": None,
                "remind_before": 30,
                "is_reminded": False
            },
            # 健康相关
            {
                "content": "晨跑5公里",
                "done": False,
                "category_id": categories["健康"].id,
                "priority": 2,
                "due_date": now + timedelta(hours=12),
                "remind_before": 30,
                "is_reminded": False
            },
            {
                "content": "预约体检",
                "done": True,
                "category_id": categories["健康"].id,
                "priority": 3,
                "due_date": now - timedelta(days=2),
                "remind_before": 1440,
                "is_reminded": True,
                "completed_at": now - timedelta(days=2, hours=-2)
            },
            # 娱乐相关
            {
                "content": "看电影",
                "done": False,
                "category_id": categories["娱乐"].id,
                "priority": 1,
                "due_date": now + timedelta(days=7),
                "remind_before": 60,
                "is_reminded": False
            },
            # 已过期任务
            {
                "content": "提交月度总结",
                "done": False,
                "category_id": categories["工作"].id,
                "priority": 3,
                "due_date": now - timedelta(days=1),
                "remind_before": 60,
                "is_reminded": True
            },
        ]

        created_count = 0
        for todo_data in todos_data:
            # 检查是否已存在相同内容的TODO
            existing = db.query(models.ToDo).filter(
                models.ToDo.content == todo_data["content"],
                models.ToDo.owner_id == user.id
            ).first()

            if existing:
                print(f"TODO '{todo_data['content']}' 已存在，跳过")
                continue

            todo = models.ToDo(
                content=todo_data["content"],
                done=todo_data["done"],
                owner_id=user.id,
                category_id=todo_data.get("category_id"),
                priority=todo_data["priority"],
                due_date=todo_data.get("due_date"),
                remind_before=todo_data["remind_before"],
                is_reminded=todo_data.get("is_reminded", False),
                completed_at=todo_data.get("completed_at"),
                created_at=now - timedelta(days=5)  # 模拟5天前创建
            )
            db.add(todo)
            created_count += 1

        db.commit()
        print(f"\n成功创建 {created_count} 个TODO")

        # 统计信息
        total_todos = db.query(models.ToDo).filter(models.ToDo.owner_id == user.id).count()
        completed_todos = db.query(models.ToDo).filter(
            models.ToDo.owner_id == user.id,
            models.ToDo.done == True
        ).count()

        print(f"\n用户 '{user.username}' 当前共有:")
        print(f"  - TODO总数: {total_todos}")
        print(f"  - 已完成: {completed_todos}")
        print(f"  - 待完成: {total_todos - completed_todos}")

        print("\n测试数据创建完成!")
        print(f"\n登录信息:")
        print(f"  邮箱: test@example.com")
        print(f"  密码: password123")
        print(f"  用户ID: {user.id}")

    except Exception as e:
        print(f"创建测试数据时出错: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 50)
    print("开始创建测试数据...")
    print("=" * 50)
    create_test_data()
