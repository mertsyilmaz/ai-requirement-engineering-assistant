from fastapi import APIRouter

from app.api.v1.analysis_controller import router as analysis_router
from app.api.v1.health_controller import router as health_router


router = APIRouter()

router.include_router(analysis_router)
router.include_router(health_router)