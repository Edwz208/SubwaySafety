from fastapi import WebSocket, WebSocketDisconnect, APIRouter, HTTPException, status, Depends
from typing import Any
import json

router = APIRouter()

class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"New connection. Total connections: {len(self.active_connections)}")
        
    async def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
        
    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                disconnected.append(connection)
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)
    
manager = ConnectionManager()

@router.websocket("/alert")
async def stream_connection(websocket: WebSocket):
    try: 
        await manager.connect(websocket)
    except Exception: 
        return
    try: 
        while True:
            data = await websocket.receive_text() # needed to handle disconnects            
    except WebSocketDisconnect:
        await manager.disconnect(websocket)

def send_alert(alert_data: dict[str, Any]):
    message = json.dumps(alert_data)
    print(f"Broadcasting alert: {message}")
    import asyncio
    asyncio.create_task(manager.broadcast(message))

@router.get("/test_alert")
async def test_alert():
    sample_alert = {
        "type": "event",
        "event": {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "name": "King St Entrance",
            "camera_id": "3",
            "event_type": "aggression",
            "description": "agression detected at King St Entrance",
            "created_at": "2024-06-01T12:34:56Z"
        }
    }
    send_alert(sample_alert)
    return {"message": "Test alert sent"}
