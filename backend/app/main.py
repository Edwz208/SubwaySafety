from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from routers.login import router as login_router
from routers.testing import router as test_router

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