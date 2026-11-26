from fastapi import APIRouter

from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.api.routes.questions import router as questions_router
from app.api.routes.retrieval import router as retrieval_router
from app.api.routes.analysis import router as analysis_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(questions_router, prefix="/questions", tags=["questions"])
api_router.include_router(retrieval_router, prefix="/retrieval", tags=["retrieval"])
api_router.include_router(analysis_router, tags=["analysis"])
