# alert.py
# Handles WebSocket connections AND fires Gemini alerts when camera_worker detects events.

from fastapi import WebSocket, WebSocketDisconnect, APIRouter, HTTPException, status, Depends
from schemas.event import EventCreate
from typing import Any
import json
import asyncio
import time
import os
import threading

router = APIRouter()

# ── Gemini cooldown — only call Gemini once per minute ───────────────────────
_last_gemini_time: float = 0.0
GEMINI_COOLDOWN_SECONDS: int = 60


# ─────────────────────────────────────────────────────────────────────────────
# CONNECTION MANAGER
# ─────────────────────────────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"New connection. Total connections: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
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


# ─────────────────────────────────────────────────────────────────────────────
# send_alert — thin wrapper around dispatch_alert for backwards compatibility
# ─────────────────────────────────────────────────────────────────────────────

def send_alert(alert_data: dict[str, Any]):
    dispatch_alert(
        events    = [alert_data.get("event", {}).get("event_type", "UNKNOWN")],
        clip_file = None,
        camera_id = str(alert_data.get("event", {}).get("camera_id", "unknown")),
    )


# ─────────────────────────────────────────────────────────────────────────────
# dispatch_alert — called by camera_worker when a critical event fires
# ─────────────────────────────────────────────────────────────────────────────

def dispatch_alert(
    events:    list[str],
    clip_file: str | None,
    camera_id: str,
):
    print(f"[alert] Dispatching alert: {events} | camera={camera_id}")

    from services.gemini import analyze_incident, analyze_video_direct
    from detection.clip_recorder import CLIPS_DIR

    # ── Step 1a: Gemini text summary (cooldown protected) ────────────────────
    global _last_gemini_time
    now = time.time()

    if now - _last_gemini_time < GEMINI_COOLDOWN_SECONDS:
        gemini_message = f"CRITICAL alert: {', '.join(events)} detected at {camera_id}."
        print(f"[alert] Gemini skipped (cooldown) — using fallback message")
    else:
        _last_gemini_time = now
        try:
            gemini_message = analyze_incident(
                event_type = events[0] if events else "UNKNOWN",
                severity   = "critical",
                location   = camera_id,
                camera_id  = camera_id,
                details    = {
                    "all_events": ", ".join(events),
                },
            )
            print(f"[alert] Gemini text: {gemini_message}")
        except Exception as e:
            gemini_message = f"CRITICAL alert: {', '.join(events)} detected at {camera_id}."
            print(f"[alert] Gemini failed, using fallback: {e}")

    # ── Step 1b: Video analysis in background after clip finishes ─────────────
    def analyze_clip_later():
        time.sleep(8)
        try:
            clip_path = os.path.join(CLIPS_DIR, clip_file)
            if os.path.exists(clip_path):
                print(f"[alert] Sending clip to Gemini for video analysis...")
                video_analysis = analyze_video_direct(clip_path)
                print(f"[alert] Gemini video analysis:\n{video_analysis}")
            else:
                print(f"[alert] Clip not found: {clip_path}")
        except Exception as e:
            print(f"[alert] Video analysis failed: {e}")

    if clip_file:
        threading.Thread(target=analyze_clip_later, daemon=True).start()

    # ── Step 2: Build payload — schema is the single source of truth ──────────
    event = EventCreate(
        camera_id       = camera_id,
        event_type      = events[0] if events else "UNKNOWN",
        message         = gemini_message,
        video_clip_path = clip_file,
    )

    payload = json.dumps({
        "type":      "alert",
        "event":     event.model_dump(),
        "timestamp": time.time(),
    })

    # ── Step 3: Broadcast to all connected dashboards ─────────────────────────
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(manager.broadcast(payload), loop)
        else:
            loop.run_until_complete(manager.broadcast(payload))
    except Exception as e:
        print(f"[alert] WebSocket broadcast failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# WEBSOCKET ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

@router.websocket("/alert")
async def stream_connection(websocket: WebSocket):
    try:
        await manager.connect(websocket)
    except Exception:
        return
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


# ─────────────────────────────────────────────────────────────────────────────
# TEST ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/test_alert")
async def test_alert():
    sample_alert = {
        "type": "event",
        "event": {
            "id":          "123e4567-e89b-12d3-a456-426614174000",
            "name":        "King St Entrance",
            "camera_id":   "3",
            "event_type":  "aggression",
            "description": "aggression detected at King St Entrance",
            "created_at":  "2024-06-01T12:34:56Z",
        }
    }
    send_alert(sample_alert)
    return {"message": "Test alert sent"}
