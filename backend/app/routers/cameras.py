from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.connection import get_db
from models.camera import Camera
from schemas.camera import CameraCreate, CameraRead, CameraUpdate

router = APIRouter()

@router.post("/cameras", response_model=CameraRead, status_code=status.HTTP_201_CREATED)
def create_camera(payload: CameraCreate, db: Session = Depends(get_db)):
    camera = Camera(**payload.model_dump())
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return {
        "id": camera.id,
        "name": camera.name,
        "url": camera.url,
        "location": camera.location,
        "is_detected": False,
    }


@router.get("/cameras", response_model=list[CameraRead])
def list_cameras(db: Session = Depends(get_db)):
    print("hi")
    cameras = [
        {
            "id": 1,
            "name": "Union Station Platform",
            "location": "Toronto Union Station",
            "is_detected": False,
            "is_online": True
        },
        {
            "id": 2,
            "name": "King St Entrance",
            "location": "King Station Entrance",
            "is_detected": False,
            "is_online": True
        },
        {
            "id": 3,
            "name": "Subway Tunnel East",
            "location": "Line 1 East Tunnel",
            "is_detected": False,
            "is_online": False
        }
    ]

    return cameras


@router.get("/cameras/{camera_id}", response_model=CameraRead)
def get_camera(camera_id: UUID, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera


@router.patch("/cameras/{camera_id}", response_model=CameraRead)
def update_camera(
    camera_id: UUID,
    payload: CameraUpdate,
    db: Session = Depends(get_db),
):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(camera, field, value)

    db.commit()
    db.refresh(camera)
    return camera


@router.delete("/cameras/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_camera(camera_id: UUID, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    db.delete(camera)
    db.commit()
    return None