from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    REFRESH_KEY: str
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080
    APP_NAME: str = "My API"
    DEBUG: bool = True
    
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env")

settings = Settings()
