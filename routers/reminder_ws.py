"""
提醒 WebSocket 路由
用于接收TODO提醒通知
"""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime

from reminder_manager import manager
from sql_app.database import get_db
from routers.auth import SECRET_KEY, ALGORITHM
from sql_app.cruds import users as crud_users
from sql_app.schemas import schemas_user

router = APIRouter()


async def get_user_from_token(token: str, db: Session) -> schemas_user.User:
    """从token获取用户信息"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = crud_users.get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user


@router.websocket("/ws/reminders")
async def websocket_endpoint(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    """
    提醒 WebSocket 连接端点
    
    使用方式:
    ws://localhost:8000/ws/reminders?token=YOUR_JWT_TOKEN
    
    接收的消息格式(JSON):
    {
        "type": "reminder",
        "todo_id": 1,
        "content": "任务内容",
        "due_date": "2024-01-01T12:00:00",
        "remind_before": 30,
        "priority": 3,
        "title": "TODO提醒",
        "message": "您的任务即将到期！"
    }
    """
    user = None
    try:
        # 验证token
        user = await get_user_from_token(token, db)
    except HTTPException as e:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # 建立连接
    await manager.connect(websocket, user.id)
    
    try:
        # 发送欢迎消息
        welcome_msg = {
            "type": "system",
            "message": f"欢迎 {user.username}！提醒服务已连接",
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send_json(welcome_msg)
        
        while True:
            # 接收客户端消息（如心跳、确认收到提醒等）
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # 处理客户端确认收到提醒
                if message.get("type") == "acknowledge":
                    todo_id = message.get("todo_id")
                    if todo_id:
                        # 可以在这里记录用户已确认提醒
                        ack_msg = {
                            "type": "system",
                            "message": f"已确认收到提醒: TODO {todo_id}",
                            "timestamp": datetime.now().isoformat()
                        }
                        await websocket.send_json(ack_msg)
                
                # 心跳响应
                elif message.get("type") == "ping":
                    pong_msg = {
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket.send_json(pong_msg)
            
            except json.JSONDecodeError:
                # 非JSON消息，当作心跳处理
                pong_msg = {
                    "type": "pong",
                    "message": "received: " + data,
                    "timestamp": datetime.now().isoformat()
                }
                await websocket.send_json(pong_msg)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, user.id)
    except Exception as e:
        print(f"WebSocket连接错误: {e}")
        manager.disconnect(websocket, user.id)


@router.websocket("/ws/reminders/ws")
async def websocket_endpoint_alt(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    """备用连接端点，兼容不同的路径配置"""
    await websocket_endpoint(websocket, token, db)
