import asyncio
from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from app.models.user import User
from app.services.ai_service import ai_service
from app.services.model_router import FREE_MODELS, MODEL_PROVIDERS, get_provider_credentials

router = APIRouter(prefix="/models", tags=["Models"])


@router.get("")
async def list_models(
    current_user: User = Depends(get_current_user),
):
    """List the AI models the backend supports and whether each has an API key configured."""
    return [
        {
            "id": model_id,
            "provider": MODEL_PROVIDERS[model_id],
            "configured": bool(get_provider_credentials(model_id)[0]),
        }
        for model_id in FREE_MODELS
    ]


@router.get("/health")
async def models_health(
    current_user: User = Depends(get_current_user),
):
    """
    Health per provider: {"groq": "healthy" | "degraded" | "down", ...}.
    Key checks are cached for a few minutes, so this is cheap to poll.
    """
    providers = sorted(set(MODEL_PROVIDERS.values()))
    statuses = await asyncio.gather(*(ai_service.check_model_health(p) for p in providers))
    return dict(zip(providers, statuses))
