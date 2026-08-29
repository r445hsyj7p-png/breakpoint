from fastapi import FastAPI

from app.api.analyzer import router as analyzer_router
from app.api.engagements import router as engagements_router
from app.api.health import router as health_router

app = FastAPI(title="Breakpoint API", version="0.1.0")

app.include_router(health_router)
app.include_router(analyzer_router)
app.include_router(engagements_router)
