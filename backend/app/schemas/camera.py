from pydantic import BaseModel, ConfigDict
from datetime import datetime

class CameraCreate(BaseModel):
    name: str
    url: str | None = None
    location: str | None = None


class CameraUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    location: str | None = None

class CameraRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str | None
    location: str | None
    last_detected_at: datetime | None