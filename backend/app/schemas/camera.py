from uuid import UUID

from pydantic import BaseModel, ConfigDict

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

    id: int # can change to uuid
    name: str
    url: str | None = None # change to not None
    location: str | None = None
    is_detected: bool