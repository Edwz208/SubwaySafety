from fastapi import FastAPI
from routers.cameras import router as cameras_router
from routers.events import router as events_router
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from routers.login import router as login_router
from routers.testing import router as test_router
from routers.alert import router as alert_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ORIGIN,
    allow_credentials=True, # allows for cookiese
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization"],
) 

app.include_router(login_router)
app.include_router(test_router)
app.include_router(alert_router)
app.include_router(cameras_router, prefix="/api")
app.include_router(events_router, prefix="/api")