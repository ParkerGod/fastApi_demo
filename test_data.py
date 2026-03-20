"""
测试数据创建脚本
使用方法：运行此脚本创建测试用户、分类和TODO数据
"""

import sys
sys.path.append('.')

from sqlalchemy.orm import Session
from sql_app.database import SessionLocal, engine, Base
from sql_app import models
from sql_app.schemas import schemas_utils
from datetime import datetime, timedelta
import bcrypt

SECRET_KEY = "wangcheng"

def get_password_hash(password: str):
    # 与users.py保持一致的加盐逻辑
    salted_password = password + SECRET_KEY
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(salted_password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def init_db():
    """初始化数据库表"""
    Base.metadata.create_all(bind=engine)
    print("数据库表初始化完成")

def create_test_user(db: Session):
    """创建测试用户"""
    # 检查用户是否已存在
    user = db.query(models.User).filter(models.User.email == "test@example.com").first()
    if user:
        print(f"测试用户已存在: ID={user.id}, email={user.email}")
        return user
    
    user = models.User(
        email="test@example.com",
        username="测试用户",
        hashed_password=get_password_hash("test123"),
        role="general",
        is_active=True,
        frequency_max=600
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"创建测试用户: ID={user.id}, email={user.email}, password=test123")
    return user

def create_test_categories(db: Session, user_id: int):
    """创建测试分类"""
    categories_data = [
        {"name": "工作", "color": "#3B82F6", "icon": "briefcase", "sort_order": 1},
        {"name": "个人", "color": "#10B981", "icon": "user", "sort_order": 2},
        {"name": "学习", "color": "#F59E0B", "icon": "book", "sort_order": 3},
        {"name": "健康", "color": "#EF4444", "icon": "heart", "sort_order": 4},
    ]
    
    categories = []
    for cat_data in categories_data:
        category = models.Category(
            name=cat_data["name"],
            color=cat_data["color"],
            icon=cat_data["icon"],
            sort_order=cat_data["sort_order"],
            owner_id=user_id
        )
        db.add(category)
        categories.append(category)
    
    db.commit()
    for cat in categories:
        db.refresh(cat)
        print(f"创建分类: ID={cat.id}, 名称={cat.name}")
    
    return categories

def create_test_todos(db: Session, user_id: int, categories):
    """创建测试TODO数据"""
    now = datetime.utcnow()
    
    todos_data = [
        # 高优先级，即将过期
        {
            "content": "完成项目报告",
            "done": False,
            "priority": 3,
            "due_date": now + timedelta(minutes=30),
            "remind_before": 60,
            "category_id": categories[0].id if categories else None
        },
        # 中优先级，未来任务
        {
            "content": "回复客户邮件",
            "done": False,
            "priority": 2,
            "due_date": now + timedelta(hours=3),
            "remind_before": 30,
            "category_id": categories[0].id if categories else None
        },
        # 低优先级
        {
            "content": "整理桌面",
            "done": False,
            "priority": 1,
            "due_date": None,
            "remind_before": 0,
            "category_id": categories[1].id if categories else None
        },
        # 已完成任务
        {
            "content": "购买生活用品",
            "done": True,
            "priority": 2,
            "due_date": now - timedelta(hours=1),
            "remind_before": 0,
            "category_id": categories[1].id if categories else None
        },
        # 学习任务
        {
            "content": "学习Python高级编程",
            "done": False,
            "priority": 2,
            "due_date": now + timedelta(days=2),
            "remind_before": 1440,  # 提前1天提醒
            "category_id": categories[2].id if categories else None
        },
        # 健康任务
        {
            "content": "跑步30分钟",
            "done": False,
            "priority": 3,
            "due_date": now + timedelta(hours=1),
            "remind_before": 15,
            "category_id": categories[3].id if categories else None
        },
        # 无分类任务
        {
            "content": "随意任务",
            "done": False,
            "priority": 2,
            "due_date": None,
            "remind_before": 0,
            "category_id": None
        },
        # 已过期任务
        {
            "content": "过期的任务",
            "done": False,
            "priority": 2,
            "due_date": now - timedelta(hours=2),
            "remind_before": 30,
            "category_id": categories[0].id if categories else None
        },
    ]
    
    todos = []
    for todo_data in todos_data:
        todo = models.ToDo(
            content=todo_data["content"],
            done=todo_data["done"],
            priority=todo_data["priority"],
            due_date=todo_data["due_date"],
            remind_before=todo_data["remind_before"],
            category_id=todo_data["category_id"],
            owner_id=user_id,
            created_at=now - timedelta(hours=len(todos))  # 模拟不同创建时间
        )
        db.add(todo)
        todos.append(todo)
    
    db.commit()
    for todo in todos:
        db.refresh(todo)
        status = "已完成" if todo.done else "待完成"
        print(f"创建TODO: ID={todo.id}, 内容={todo.content}, 状态={status}")
    
    return todos

def main():
    print("=" * 50)
    print("开始创建测试数据")
    print("=" * 50)
    
    # 初始化数据库
    init_db()
    
    # 创建数据库会话
    db = SessionLocal()
    
    try:
        # 创建测试用户
        print("\n" + "-" * 30)
        print("创建测试用户")
        print("-" * 30)
        user = create_test_user(db)
        
        # 创建测试分类
        print("\n" + "-" * 30)
        print("创建测试分类")
        print("-" * 30)
        categories = create_test_categories(db, user.id)
        
        # 创建测试TODO
        print("\n" + "-" * 30)
        print("创建测试TODO")
        print("-" * 30)
        todos = create_test_todos(db, user.id, categories)
        
        print("\n" + "=" * 50)
        print("测试数据创建完成！")
        print("=" * 50)
        print(f"\n测试账号信息:")
        print(f"  邮箱: test@example.com")
        print(f"  密码: test123")
        print(f"\n创建的统计:")
        print(f"  分类数量: {len(categories)}")
        print(f"  TODO数量: {len(todos)}")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()