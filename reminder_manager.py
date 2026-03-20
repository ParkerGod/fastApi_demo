"""
提醒管理器模块
包含：WebSocket连接管理、定时任务、提醒推送
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Set
from fastapi import WebSocket
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from sql_app import models
from sql_app.database import SessionLocal
from sql_app.cruds import utils as crud_utils


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 存储用户ID到WebSocket连接的映射 {user_id: set(websockets)}
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # 存储token到user_id的映射
        self.token_to_user: Dict[str, int] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """连接建立时调用"""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        print(f"用户 {user_id} 已连接，当前连接数: {len(self.active_connections[user_id])}")
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        """连接断开时调用"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            print(f"用户 {user_id} 断开连接，剩余连接数: {len(self.active_connections.get(user_id, []))}")
    
    async def send_personal_message(self, message: dict, user_id: int):
        """向特定用户发送消息"""
        if user_id in self.active_connections:
            message_json = json.dumps(message, ensure_ascii=False, default=str)
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(message_json)
                except Exception as e:
                    print(f"发送消息给用户 {user_id} 失败: {e}")
                    # 从连接池中移除失效连接
                    self.active_connections[user_id].discard(websocket)
    
    async def broadcast(self, message: dict):
        """广播消息给所有用户"""
        message_json = json.dumps(message, ensure_ascii=False, default=str)
        for user_id in list(self.active_connections.keys()):
            for websocket in list(self.active_connections[user_id]):
                try:
                    await websocket.send_text(message_json)
                except Exception as e:
                    print(f"广播消息给用户 {user_id} 失败: {e}")
                    self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]


# 全局连接管理器实例
manager = ConnectionManager()


class ReminderScheduler:
    """定时提醒任务调度器"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        # 提醒任务执行间隔（秒）
        self.check_interval = 60  # 每分钟检查一次
    
    async def check_and_send_reminders(self):
        """检查并发送提醒"""
        print(f"[{datetime.now()}] 开始检查待提醒的TODO...")
        
        db = None
        try:
            # 直接创建数据库会话
            db = SessionLocal()
            
            # 获取需要提醒的TODO列表
            todos_to_remind = crud_utils.get_todos_for_reminder(db)
            
            if todos_to_remind:
                print(f"发现 {len(todos_to_remind)} 个待提醒的TODO")
                
                for todo in todos_to_remind:
                    # 获取用户信息
                    user_id = todo.owner_id
                    
                    # 构造提醒消息
                    reminder_message = {
                        "type": "reminder",
                        "todo_id": todo.id,
                        "content": todo.content,
                        "due_date": todo.due_date.isoformat() if todo.due_date else None,
                        "remind_before": todo.remind_before,
                        "priority": todo.priority,
                        "title": "TODO提醒",
                        "message": f"您的任务 \"{todo.content}\" 即将到期！"
                    }
                    
                    # 推送提醒
                    await manager.send_personal_message(reminder_message, user_id)
                    print(f"已向用户 {user_id} 发送提醒: {todo.content}")
                    
                    # 标记为已提醒
                    crud_utils.mark_as_reminded(db, todo.id)
            else:
                print("没有需要提醒的TODO")
                
        except Exception as e:
            print(f"提醒检查失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if db:
                db.close()
    
    def start(self):
        """启动定时任务"""
        # 添加定时任务
        self.scheduler.add_job(
            self.check_and_send_reminders,
            trigger=IntervalTrigger(seconds=self.check_interval),
            id="todo_reminder_check",
            name="检查TODO提醒",
            replace_existing=True
        )
        
        # 立即执行一次检查
        self.scheduler.add_job(
            self.check_and_send_reminders,
            id="todo_reminder_initial_check",
            name="初始提醒检查",
            replace_existing=True
        )
        
        self.scheduler.start()
        print(f"定时提醒任务已启动，检查间隔: {self.check_interval}秒")
    
    def stop(self):
        """停止定时任务"""
        self.scheduler.shutdown()
        print("定时提醒任务已停止")


# 测试定时任务（不依赖WebSocket）
def test_reminder_scheduler():
    """测试提醒调度器"""
    scheduler = ReminderScheduler()
    
    # 运行一次检查
    import asyncio
    asyncio.run(scheduler.check_and_send_reminders())
    print("测试完成")


if __name__ == "__main__":
    test_reminder_scheduler()
