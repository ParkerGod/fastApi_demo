import asyncio
import time

import uvicorn
from fastapi import FastAPI, WebSocket
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import WebSocketRoute
from sql_app import models
from sql_app.database import engine
from routers import auth, users, utils, websocket
from routers.websocket import todo_reminder_websocket, check_and_send_reminders

# 建表
models.Base.metadata.create_all(bind=engine)

app = FastAPI(routes=websocket.routes)

# 添加TODO提醒WebSocket路由
app.add_websocket_route("/ws/todo-reminder/{user_id}", todo_reminder_websocket)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(utils.router)

# 跨域配置
origins = ['*']
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    return {"message": f"Hello World! now is {now}"}


@app.on_event("startup")
async def startup_event():
    """启动后台任务"""
    # 启动定时提醒任务
    asyncio.create_task(check_and_send_reminders())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
