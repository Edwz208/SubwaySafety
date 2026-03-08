from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class EventCreate(BaseModel):
    camera_id: int
    event_type: str
    snapshot_path: str | None = None
    video_clip_path: str | None = None

class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: UUID
    occurred_at: datetime
    event_type: str
    video_clip_path: str | None
    description: str | None