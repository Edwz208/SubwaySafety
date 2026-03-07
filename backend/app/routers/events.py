from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from db.connection import get_db
from models.camera import Camera
from models.event import Event
from schemas.event import EventCreate, EventRead
from routers.alert import send_alert          # ← connects detection → dashboard
from services.gemini import analyze_incident  # ← Gemini summary per alert

router = APIRouter(prefix="/events", tags=["events"])


# ─────────────────────────────────────────────
# POST /api/events
# Called by the detection pipeline when classifiers.py detects something.
# Flow:
#   1. Verify camera exists
#   2. Save event to DB
#   3. Call Gemini to generate a human-readable summary
#   4. Fire WebSocket alert to dashboard
# ─────────────────────────────────────────────
@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreate, db: Session = Depends(get_db)):
    # Verify the camera exists before saving
    camera = db.query(Camera).filter(Camera.id == payload.camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    # Save event to DB
    event = Event(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)

    # ── Generate Gemini summary ──
    # analyze_incident() takes the event and returns a plain text summary.
    # We update the DB record with the summary after getting it.
    try:
        summary = analyze_incident(
            event_type=event.event_type,
            severity=event.severity,
            location=camera.location,
            camera_id=str(event.camera_id),
            details=event.details if hasattr(event, "details") else {},
        )
        event.summary = summary
        db.commit()
        db.refresh(event)
    except Exception as e:
        # Don't crash if Gemini fails — alert still fires without summary
        print(f"[events] Gemini summary failed: {e}")
        summary = f"{event.event_type} detected at {camera.location}."

    # ── Fire WebSocket alert to all connected dashboard clients ──
    # This calls send_alert() in routers/alert.py which broadcasts
    # the event to every browser tab with the dashboard open.
    send_alert({
        "id":           str(event.id),
        "camera_id":    str(event.camera_id),
        "location":     camera.location,
        "severity":     event.severity,
        "event_type":   event.event_type,
        "summary":      summary,
        "snapshot_url": event.snapshot_url if hasattr(event, "snapshot_url") else None,
        "timestamp":    event.occurred_at.isoformat(),
        "acknowledged": False,
    })

    return event


# ─────────────────────────────────────────────
# GET /api/events
# Returns list of events — used by IncidentLog table in dashboard.
# Optional filter by camera_id.
# ─────────────────────────────────────────────
@router.get("", response_model=list[EventRead])
def list_events(
    camera_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Event)
    if camera_id is not None:
        query = query.filter(Event.camera_id == camera_id)
    events = query.order_by(Event.occurred_at.desc()).limit(limit).all()
    return events


# ─────────────────────────────────────────────
# GET /api/events/{event_id}
# Returns one specific event — used by incident detail view.
# ─────────────────────────────────────────────
@router.get("/{event_id}", response_model=EventRead)
def get_event(event_id: UUID, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


# ─────────────────────────────────────────────
# PATCH /api/events/{event_id}/acknowledge
# Called when staff clicks Acknowledge on the dashboard alert card.
# ─────────────────────────────────────────────
@router.patch("/{event_id}/acknowledge", response_model=EventRead)
def acknowledge_event(event_id: UUID, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    event.acknowledged = True
    db.commit()
    db.refresh(event)
    return event


# ─────────────────────────────────────────────
# GET /api/events/heatmap
# Returns incident counts per location for HeatmapWidget.jsx
# ─────────────────────────────────────────────
@router.get("/heatmap/summary")
def get_heatmap(db: Session = Depends(get_db)):
    from sqlalchemy import func
    from models.camera import Camera as CameraModel

    # Join events with cameras to get location names
    results = (
        db.query(CameraModel.location, func.count(Event.id).label("count"))
        .join(Event, Event.camera_id == CameraModel.id)
        .group_by(CameraModel.location)
        .order_by(func.count(Event.id).desc())
        .all()
    )
    return [{"location": row.location, "count": row.count} for row in results]
