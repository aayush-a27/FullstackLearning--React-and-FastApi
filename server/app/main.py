import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.core.redis import init_redis, close_redis
from app.core.security_headers import SecurityHeadersMiddleware
from app.routers import auth, users, chats, messages, pdfs, models
import logging

settings = get_settings()
logger = logging.getLogger("uvicorn.error")

# Send this app's own loggers to uvicorn's handlers, so background work
# (PDF indexing, model fallbacks) shows up in the server output.
_app_logger = logging.getLogger("app")
_app_logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
_app_logger.handlers = logging.getLogger("uvicorn.error").handlers or _app_logger.handlers
_app_logger.propagate = not _app_logger.handlers

def _run_migrations():
    """
    Bring the database up to the latest Alembic revision.

    Blocking (Alembic is sync), so it's called via asyncio.to_thread below.
    """
    from alembic import command
    from alembic.config import Config

    alembic_ini = Path(__file__).resolve().parent.parent / "alembic.ini"
    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(alembic_ini.parent / "alembic"))
    command.upgrade(config, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan -- startup and shutdown events."""
    # === STARTUP ===
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Apply database migrations (Alembic owns the schema — see alembic/versions)
    db_ready = False
    try:
        await asyncio.to_thread(_run_migrations)
        db_ready = True
        logger.info("Database schema is up to date")
    except Exception as e:
        logger.error(f"Database migration failed: {e}")

    # Initialize Redis (optional -- gracefully handle if not available)
    try:
        await init_redis()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis not available: {e}. Running without cache/sessions.")

    # Create uploads directory
    import os
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info(f"Upload directory: {settings.UPLOAD_DIR}")

    # Restart any PDF indexing that a previous run left unfinished
    if db_ready:
        try:
            from app.services.pdf_processing import requeue_unfinished
            await requeue_unfinished()
        except Exception as e:
            logger.error(f"Could not requeue unfinished PDF processing: {e}")

    yield

    # === SHUTDOWN ===
    try:
        await close_redis()
        logger.info("Redis disconnected")
    except Exception:
        pass
    logger.info(f"{settings.APP_NAME} stopped")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Chat with your PDFs using AI -- multi-model support with smart switching",
    lifespan=lifespan,
)

# === Security headers ===
# (replaces the payload encryption from the original plan — see SECURITY.md)
app.add_middleware(SecurityHeadersMiddleware, production=not settings.DEBUG)

# === CORS Middleware ===
# Credentials are sent with requests, so the origin list must stay explicit;
# "*" is silently ignored by browsers when allow_credentials is on.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)

# === Include Routers ===
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(chats.router, prefix=settings.API_V1_PREFIX)
app.include_router(messages.router, prefix=settings.API_V1_PREFIX)
app.include_router(pdfs.router, prefix=settings.API_V1_PREFIX)
app.include_router(models.router, prefix=settings.API_V1_PREFIX)


# === Health Check ===
@app.get("/", tags=["Health"])
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}