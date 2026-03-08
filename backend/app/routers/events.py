from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from db.connection import get_db
from models.event import Event
from schemas.event import EventRead

router = APIRouter()

# ─────────────────────────────────────────────
# GET /api/events
# Returns list of events — used by IncidentLog table in dashboard.
# Optional filter by camera_id.
# ─────────────────────────────────────────────
@router.get("/events", response_model=list[EventRead])
def list_events(
    camera_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Event)
    if camera_id is not None:
        query = query.filter(Event.camera_id == camera_id)
    events = query.order_by(Event.occurred_at.desc()).limit(limit).all()
    # events = [
    #         {
    #             "id": 1,
    #             "camera_id": 1,
    #             "occurred_at": "2024-06-01T12:00:00Z",
    #             "event_type": "Intrusion",
    #             "video_clip_path": "/path/to/video1.mp4",
    #             "description": "Person detected in restricted area"
    #         },
    #         {
    #             "id": 2,
    #             "camera_id": 2,
    #             "occurred_at": "2024-06-01T12:05:00Z",
    #             "event_type": "Loitering",
    #             "video_clip_path": "/path/to/video2.mp4",
    #             "description": "Person loitering for more than 10 minutes"
    #         }
    #     ]
    return events


# ─────────────────────────────────────────────
# GET /api/events/{event_id}
# Returns one specific event — used by incident detail view.
# ─────────────────────────────────────────────
@router.get("/events/{event_id}", response_model=EventRead)
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event