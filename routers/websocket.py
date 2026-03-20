#!/usr/bin/env python
# coding=utf-8
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Set
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from starlette.endpoints import WebSocketEndpoint, HTTPEndpoint
from starlette.responses import HTMLResponse
from starlette.routing import Route, WebSocketRoute

from sql_app.database import get_db, SessionLocal
from sql_app import cruds

# 存储用户WebSocket连接
user_connections: Dict[int, Set[WebSocket]] = {}


class TodoReminderWebSocket:
    """TODO提醒WebSocket管理器"""

    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_reminder(self, user_id: int, message: dict):
        """向指定用户发送提醒"""
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.add(connection)

            # 清理断开的连接
            for conn in disconnected:
                self.active_connections[user_id].discard(conn)

    async def broadcast(self, message: dict):
        """广播消息给所有连接的用户"""
        for user_id in list(self.active_connections.keys()):
            await self.send_reminder(user_id, message)


# 创建WebSocket管理器实例
reminder_manager = TodoReminderWebSocket()


async def check_and_send_reminders():
    """后台任务：检查并发送提醒
    
    根据每项TODO的 remind_before 字段个性化提醒
    """
    while True:
        try:
            # 创建数据库会话
            db = SessionLocal()
            try:
                # 获取所有在线用户
                for user_id in list(reminder_manager.active_connections.keys()):
                    # 获取该用户的即将到期提醒（根据每项TODO的 remind_before）
                    todos = cruds.get_upcoming_reminders(db, user_id, max_check_minutes=1440)

                    for todo in todos:
                        if todo.due_date:
                            now = datetime.utcnow()
                            minutes_left = int((todo.due_date - now).total_seconds() / 60)
                            
                            # 计算实际提前提醒时间（可能早于 remind_before，但不会晚于）
                            actual_remind_before = todo.remind_before
                            if minutes_left < actual_remind_before:
                                actual_remind_before = minutes_left

                            reminder_message = {
                                "type": "reminder",
                                "data": {
                                    "id": todo.id,
                                    "content": todo.content,
                                    "due_date": todo.due_date.isoformat() if todo.due_date else None,
                                    "priority": todo.priority,
                                    "minutes_left": minutes_left,
                                    "remind_before": todo.remind_before  # 添加设置的提醒时间
                                },
                                "message": f"任务 '{todo.content}' 将在 {minutes_left} 分钟后到期（提前{todo.remind_before}分钟提醒）"
                            }

                            await reminder_manager.send_reminder(user_id, reminder_message)

                            # 标记为已提醒
                            cruds.mark_reminded(db, todo.id, user_id)

            finally:
                db.close()

        except Exception as e:
            print(f"Reminder check error: {e}")

        # 每分钟检查一次
        await asyncio.sleep(60)


# ==================== WebSocket 路由 ====================

async def todo_reminder_websocket(websocket: WebSocket, user_id: int):
    """TODO提醒WebSocket端点"""
    await reminder_manager.connect(websocket, user_id)
    try:
        while True:
            # 保持连接并接收心跳
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        reminder_manager.disconnect(websocket, user_id)


# ==================== HTML 测试页面 ====================

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>TODO Reminder WebSocket Test</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            .reminder {
                background: #fef3c7;
                border-left: 4px solid #f59e0b;
                padding: 10px;
                margin: 10px 0;
                border-radius: 4px;
            }
            .connected {
                color: #10b981;
            }
            .disconnected {
                color: #ef4444;
            }
            #messages {
                border: 1px solid #e5e7eb;
                padding: 10px;
                min-height: 200px;
                max-height: 400px;
                overflow-y: auto;
                background: #f9fafb;
            }
        </style>
    </head>
    <body>
        <h1>TODO Reminder WebSocket Test</h1>
        <div>
            <label>User ID: </label>
            <input type="number" id="userId" placeholder="输入用户ID" value="1" />
            <button onclick="connect()">连接</button>
            <button onclick="disconnect()">断开</button>
            <span id="status" class="disconnected">未连接</span>
        </div>
        <h2>提醒消息:</h2>
        <div id="messages"></div>

        <script>
            let ws = null;
            let pingInterval = null;

            function connect() {
                const userId = document.getElementById("userId").value;
                if (!userId) {
                    alert("请输入用户ID");
                    return;
                }

                ws = new WebSocket(`ws://localhost:8000/ws/todo-reminder/${userId}`);

                ws.onopen = function() {
                    document.getElementById("status").textContent = "已连接";
                    document.getElementById("status").className = "connected";
                    addMessage("系统", "WebSocket连接已建立");

                    // 发送心跳
                    pingInterval = setInterval(() => {
                        if (ws && ws.readyState === WebSocket.OPEN) {
                            ws.send(JSON.stringify({type: "ping"}));
                        }
                    }, 30000);
                };

                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    if (data.type === "pong") {
                        return;
                    }
                    if (data.type === "reminder") {
                        addReminder(data);
                    } else {
                        addMessage("收到", JSON.stringify(data));
                    }
                };

                ws.onclose = function() {
                    document.getElementById("status").textContent = "已断开";
                    document.getElementById("status").className = "disconnected";
                    addMessage("系统", "WebSocket连接已关闭");
                    if (pingInterval) {
                        clearInterval(pingInterval);
                    }
                };

                ws.onerror = function(error) {
                    addMessage("错误", "WebSocket发生错误");
                };
            }

            function disconnect() {
                if (ws) {
                    ws.close();
                    ws = null;
                }
            }

            function addMessage(from, text) {
                const messages = document.getElementById("messages");
                const div = document.createElement("div");
                div.innerHTML = `<strong>${from}:</strong> ${text}`;
                messages.appendChild(div);
                messages.scrollTop = messages.scrollHeight;
            }

            function addReminder(data) {
                const messages = document.getElementById("messages");
                const div = document.createElement("div");
                div.className = "reminder";
                div.innerHTML = `
                    <strong>⏰ 任务提醒</strong><br>
                    任务: ${data.data.content}<br>
                    优先级: ${data.data.priority === 3 ? "高" : data.data.priority === 2 ? "中" : "低"}<br>
                    剩余时间: ${data.data.minutes_left} 分钟<br>
                    <small>${data.message}</small>
                `;
                messages.appendChild(div);
                messages.scrollTop = messages.scrollHeight;
            }
        </script>
    </body>
</html>
"""


class ReminderPage(HTTPEndpoint):
    async def get(self, request):
        return HTMLResponse(html)


# ==================== 聊天室 WebSocket (原有功能) ====================

info = {}

chat_html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off" placeholder="" />
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            document.getElementById("messageText").placeholder="第一次输入内容为昵称";

            var ws = new WebSocket("ws://localhost:8000/ws");

            // 接收
            ws.onmessage = function(event) {
                // 获取id为messages的ul标签内
                var messages = document.getElementById('messages')
                // 创建li标签
                var message = document.createElement('li')
                // 创建内容
                var content = document.createTextNode(event.data)
                // 内容添加到li标签内
                message.appendChild(content)
                // li标签添加到ul标签内
                messages.appendChild(message)
            };

            var name = 0;
            // 发送
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()

                if (name == 0){
                    document.getElementById("messageText").placeholder="";
                    name = 1;
                }
            }
        </script>
    </body>
</html>
"""


class Chatpage(HTTPEndpoint):
    async def get(self, request):
        return HTMLResponse(chat_html)


class Echo(WebSocketEndpoint):
    encoding = "text"

    # 修改socket
    async def alter_socket(self, websocket):
        socket_str = str(websocket)[1:-1]
        socket_list = socket_str.split(' ')
        socket_only = socket_list[3]
        return socket_only

    # 连接 存储
    async def on_connect(self, websocket):
        await websocket.accept()

        # 用户输入名称
        name = await websocket.receive_text()

        socket_only = await self.alter_socket(websocket)
        # 添加连接池 保存用户名
        info[socket_only] = [f'{name}', websocket]

        # 先循环 告诉之前的用户有新用户加入了
        for wbs in info:
            await info[wbs][1].send_text(f"{info[socket_only][0]}-加入了聊天室")

    # 收发
    async def on_receive(self, websocket, data):
        socket_only = await self.alter_socket(websocket)

        for wbs in info:
            await info[wbs][1].send_text(f"{info[socket_only][0]}: {data}")

    # 断开 删除
    async def on_disconnect(self, websocket, close_code):
        socket_only = await self.alter_socket(websocket)
        # 删除连接池
        info.pop(socket_only, None)


# ==================== 路由配置 ====================

routes = [
    Route("/chat", Chatpage),
    Route("/todo-reminder", ReminderPage),
    WebSocketRoute("/ws", Echo),
]
