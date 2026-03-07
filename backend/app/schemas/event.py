from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class EventCreate(BaseModel):
    camera_id: UUID
    event_type: str
    confidence: float | None = None
    snapshot_path: str | None = None
    video_clip_path: str | None = None
    metadata_json: dict | None = None


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    camera_id: UUID
    occurred_at: datetime
    event_type: str
    confidence: float | None
    snapshot_path: str | None
    video_clip_path: str | None
    metadata_json: dict | None