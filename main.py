import time
import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from sql_app import models
from sql_app.database import engine, SessionLocal
from routers import auth, users, utils, websocket, reminder_ws
from reminder_manager import ReminderScheduler

# 建表
models.Base.metadata.create_all(bind=engine)
app = FastAPI(routes=websocket.routes, title="TODO API with Reminders")
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(utils.router)
app.include_router(reminder_ws.router)

# 跨域配置
origins = ['*']
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 数据库会话生成器
# 定时任务调度器
scheduler = ReminderScheduler()


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    # 启动定时提醒任务
    scheduler.start()
    print("=" * 50)
    print("服务已启动!")
    print("定时提醒任务已激活")
    print("WebSocket提醒地址: ws://localhost:8000/ws/reminders")
    print("API文档: http://localhost:8000/docs")
    print("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    scheduler.stop()
    print("服务已关闭")


@app.get("/")
async def root():
    now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    return {
        "message": f"Hello World! now is {now}",
        "services": {
            "api_docs": "/docs",
            "websocket_reminders": "/ws/reminders",
            "chat_room": "/chat"
        }
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
