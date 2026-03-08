from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from db.connection import get_db
from models.camera import Camera
from schemas.camera import CameraCreate, CameraRead, CameraUpdate

router = APIRouter()


@router.post("/cameras", response_model=CameraRead, status_code=status.HTTP_201_CREATED)
async def create_camera(
    payload: CameraCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    camera = Camera(**payload.model_dump())
    db.add(camera)
    db.commit()
    db.refresh(camera)

    if camera.url:
        await request.app.state.worker_manager.start_worker(
            camera_id=camera.id,
            camera_url=camera.url,
            camera_name=camera.name,
        )

    return camera


@router.get("/cameras", response_model=list[CameraRead])
async def list_cameras(db: Session = Depends(get_db)):
    cameras = db.query(Camera).order_by(Camera.id).all()
    return cameras


@router.patch("/cameras/{camera_id}", response_model=CameraRead)
async def update_camera(
    camera_id: int,
    payload: CameraUpdate,
    request: Request,
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

    if camera.url:
        await request.app.state.worker_manager.restart_worker(
            camera_id=camera.id,
            camera_url=camera.url,
            camera_name=camera.name,
        )
    else:
        await request.app.state.worker_manager.stop_worker(camera.id)

    return camera


@router.delete("/cameras/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    camera_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    await request.app.state.worker_manager.stop_worker(camera_id)

    db.delete(camera)
    db.commit()
    return None