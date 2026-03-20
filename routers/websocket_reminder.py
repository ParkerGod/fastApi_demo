from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.endpoints import WebSocketEndpoint
from starlette.routing import WebSocketRoute
from routers.reminder import connect_websocket, disconnect_websocket, start_reminder_scheduler

router = APIRouter()


@router.websocket("/ws/reminder/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await connect_websocket(websocket, user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        disconnect_websocket(websocket, user_id)


routes = [
    WebSocketRoute("/ws/reminder/{user_id}", websocket_endpoint),
]


async def startup_event():
    await start_reminder_scheduler()
