from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from core.config import settings
from db.connection import SessionLocal
from models.camera import Camera
from routers.cameras import router as cameras_router
from routers.events import router as events_router
from routers.login import router as login_router
from routers.testing import router as test_router
from routers.alert import router as alert_router, set_main_loop
from services.worker_manager import WorkerManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    set_main_loop(loop)

    app.state.worker_manager = WorkerManager()

    db: Session = SessionLocal()
    try:
        cameras = db.query(Camera).order_by(Camera.id).all()
        for camera in cameras:
            if camera.url:
                await app.state.worker_manager.start_worker(
                    camera_id=camera.id,
                    camera_url=camera.url,
                    camera_name=camera.name,
                )
    finally:
        db.close()

    yield

    await app.state.worker_manager.shutdown()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(login_router)
app.include_router(test_router)
app.include_router(alert_router)
app.include_router(cameras_router)
app.include_router(events_router)