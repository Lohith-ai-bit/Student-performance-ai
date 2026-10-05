"""Application configuration loaded from environment variables / .env files."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BASE_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_NAME: str = "Student Performance AI API"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+psycopg://spa_user:spa_password@localhost:5432/student_performance"

    # Auth
    JWT_SECRET: str = "change-me-in-real-environments"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000"

    # Redis (batch job queue / background workers)
    REDIS_URL: str = "redis://localhost:6379/0"

    # ML
    ML_ARTIFACTS_DIR: str = str(BASE_DIR.parent / "ml" / "artifacts")

    # Risk classification thresholds (risk_probability ranges, configurable; see core/risk_config.py)
    RISK_THRESHOLDS_LOW: float = 0.25
    RISK_THRESHOLDS_MEDIUM: float = 0.50
    RISK_THRESHOLDS_HIGH: float = 0.75

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
