import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
from fastapi import WebSocket
from sqlalchemy.orm import Session
from sql_app.database import SessionLocal
from sql_app import cruds

active_connections: Dict[int, List[WebSocket]] = {}


async def connect_websocket(websocket: WebSocket, user_id: int):
    await websocket.accept()
    if user_id not in active_connections:
        active_connections[user_id] = []
    active_connections[user_id].append(websocket)


def disconnect_websocket(websocket: WebSocket, user_id: int):
    if user_id in active_connections:
        if websocket in active_connections[user_id]:
            active_connections[user_id].remove(websocket)


async def send_reminder(user_id: int, todo_content: str, due_date: datetime):
    if user_id in active_connections:
        message = f"提醒: 任务 \"{todo_content}\" 即将到期 ({due_date.strftime('%Y-%m-%d %H:%M')})"
        for connection in active_connections[user_id]:
            try:
                await connection.send_text(message)
            except:
                pass


async def check_reminders():
    while True:
        db = SessionLocal()
        try:
            todos = cruds.get_todos_for_reminder(db)
            for todo in todos:
                await send_reminder(todo.owner_id, todo.content, todo.due_date)
                cruds.mark_todo_reminded(db, todo.id)
        finally:
            db.close()
        
        await asyncio.sleep(60)


async def start_reminder_scheduler():
    asyncio.create_task(check_reminders())
