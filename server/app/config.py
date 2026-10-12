from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    APP_NAME: str = "Green Book AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Database — PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pdf_chat_ai"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Cookies — Secure requires HTTPS, so it's off for local http://localhost
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"

    # JWT
    JWT_SECRET_KEY: str = "super-secret-jwt-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # PDF Upload
    MAX_PDF_SIZE_MB: int = 50
    UPLOAD_DIR: str = "uploads"  # used only when R2 isn't configured

    # Cloudflare R2 for uploaded PDFs (see app/services/file_storage.py).
    # Leave empty to keep files in UPLOAD_DIR instead.
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET: str = ""

    # AI Model API Keys (optional — set via .env)
    GOOGLE_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    NEMOTRON_API_KEY: str = ""
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        # Old .env files may still list settings that were removed
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
