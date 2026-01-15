from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websockets.connection_manager import manager
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive and listen for any client messages (ping/ack)
            data = await websocket.receive_text()
            # Optional: handle client messages
            # await manager.send_personal_message(f"You wrote: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error for {user_id}: {e}")
        # manager.disconnect(websocket, user_id) # Ensure cleanup
