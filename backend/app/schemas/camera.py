from uuid import UUID
from pydantic import BaseModel, ConfigDict


class CameraCreate(BaseModel):
    name: str
    rtsp_url: str
    location: str | None = None
    is_active: bool = True


class CameraUpdate(BaseModel):
    name: str | None = None
    rtsp_url: str | None = None
    location: str | None = None
    is_active: bool | None = None


class CameraRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    rtsp_url: str
    location: str | None
    is_active: bool