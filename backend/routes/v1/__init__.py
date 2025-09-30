"""V1 API routes."""

from fastapi import APIRouter

from .reviews import router as reviews_router
from .metrics import router as metrics_router
from .healthcheck import router as healthcheck_router

router = APIRouter()

# Include endpoint-specific routers
router.include_router(healthcheck_router)
router.include_router(reviews_router)
router.include_router(metrics_router)
