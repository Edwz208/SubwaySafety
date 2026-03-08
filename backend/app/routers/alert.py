# routers/alert.py

from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from typing import Any
import json
import asyncio
import time
import os
import threading

from db.connection import SessionLocal
from models.event import Event

# adjust these imports to match your actual project structure
from services.gemini import analyze_video
from pathlib import Path
CLIPS_DIR = Path("clips")

router = APIRouter()

_last_gemini_time: float = 0.0
GEMINI_COOLDOWN_SECONDS: int = 60
_main_loop: asyncio.AbstractEventLoop | None = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"New connection. Total connections: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"Disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: str) -> None:
        disconnected: list[WebSocket] = []

        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"[broadcast] Failed to send to one websocket: {e}")
                disconnected.append(connection)

        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)


manager = ConnectionManager()


def broadcast_json(payload: dict[str, Any]) -> None:
    try:
        if _main_loop and _main_loop.is_running():
            asyncio.run_coroutine_threadsafe(
                manager.broadcast(json.dumps(payload)),
                _main_loop,
            )
        else:
            print("[alert] No running main loop available for broadcast")
    except Exception as e:
        print(f"[alert] WebSocket broadcast failed: {e}")


def send_alert(alert_data: dict[str, Any]) -> None:
    event_data = alert_data.get("event", {})
    dispatch_alert(
        events=[event_data.get("event_type", "UNKNOWN")],
        clip_file=event_data.get("video_clip_path"),
        camera_id=int(event_data.get("camera_id", 0)),
    )


def dispatch_alert(events: list[str], clip_file: str | None, camera_id: int) -> None:
    global _last_gemini_time

    db = SessionLocal()
    saved_event: Event | None = None

    try:
        saved_event = Event(
            camera_id=camera_id,
            event_type=events[0] if events else "UNKNOWN",
            video_clip_path=clip_file,
        )
        db.add(saved_event)
        db.commit()
        db.refresh(saved_event)

        payload = {
            "type": "event",
            "event": {
                "id": saved_event.id,
                "camera_id": saved_event.camera_id,
                "event_type": saved_event.event_type,
                "video_clip_path": saved_event.video_clip_path,
                "occurred_at": (
                    saved_event.occurred_at.isoformat()
                    if saved_event.occurred_at
                    else None
                ),
            },
            "timestamp": time.time(),
        }

        broadcast_json(payload)
        print(f"[dispatch_alert] Event saved and broadcast: {payload}")

    except Exception as e:
        db.rollback()
        print(f"[dispatch_alert] Failed to save event: {e}")
        return
    finally:
        db.close()

    def analyze_clip_later(event_id: int, clip_filename: str) -> None:
        global _last_gemini_time

        try:
            time.sleep(8)

            if not clip_filename:
                return

            now = time.time()
            if now - _last_gemini_time < GEMINI_COOLDOWN_SECONDS:
                print("[alert] Gemini cooldown active, skipping video analysis")
                return

            clip_path = CLIPS_DIR / clip_file


            if not os.path.exists(clip_path):
                print(f"[alert] Clip not found: {clip_path}")
                return

            print(f"[alert] Sending clip to Gemini for analysis: {clip_path}")
            gemini_message = analyze_video(clip_path)
            _last_gemini_time = time.time()

            print(f"[alert] Gemini video analysis:\n{gemini_message}")

            db2 = SessionLocal()
            try:
                event_row = db2.query(Event).filter(Event.id == event_id).first()
                if event_row:
                    event_row.description = gemini_message
                    db2.commit()
            finally:
                db2.close()

            analysis_payload = {
                "type": "event_analysis",
                "event_id": event_id,
                "camera_id": camera_id,
                "description": gemini_message,
                "timestamp": time.time(),
            }
            broadcast_json(analysis_payload)

        except Exception as e:
            print(f"[alert] Video analysis failed: {e}")

    if clip_file and saved_event is not None:
        threading.Thread(
            target=analyze_clip_later,
            args=(saved_event.id, clip_file),
            daemon=True,
        ).start()


@router.websocket("/alert")
async def stream_connection(websocket: WebSocket):
    try:
        await manager.connect(websocket)
    except Exception as e:
        print(f"[websocket] connect failed: {e}")
        return

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        print(f"[websocket] error: {e}")
        await manager.disconnect(websocket)


@router.get("/test_alert")
async def test_alert():
    dispatch_alert(
        events=["aggression"],
        clip_file=None,
        camera_id=3,
    )
    return {"message": "Test alert sent"}