from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analyzer import router as analyzer_router
from app.api.engagements import router as engagements_router
from app.api.health import router as health_router
from app.api.techniques import router as techniques_router
from app.core.config import settings

app = FastAPI(title="Breakpoint API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(health_router)
app.include_router(analyzer_router)
app.include_router(engagements_router)
app.include_router(techniques_router)
