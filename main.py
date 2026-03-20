import time

import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from sql_app import models
from sql_app.database import engine
from routers import auth, users, utils, websocket
from routers import websocket_reminder
from routers.websocket_reminder import startup_event

models.Base.metadata.create_all(bind=engine)
app = FastAPI(routes=websocket.routes)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(utils.router)
app.include_router(websocket_reminder.router)

origins = ['*']
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    await startup_event()


@app.get("/")
async def root():
    now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    return {"message": f"Hello World! now is {now}"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
