from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analyzer import router as analyzer_router
from app.api.capabilities import router as capabilities_router
from app.api.engagements import router as engagements_router
from app.api.health import router as health_router
from app.api.mitre_import import router as mitre_import_router
from app.api.portfolio import router as portfolio_router
from app.api.sales_briefing import router as sales_briefing_router
from app.api.techniques import router as techniques_router
from app.core.config import settings

app = FastAPI(title="Breakpoint API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type"],
)

app.include_router(health_router)
app.include_router(analyzer_router)
app.include_router(engagements_router)
app.include_router(techniques_router)
app.include_router(portfolio_router)
app.include_router(capabilities_router)
app.include_router(sales_briefing_router)
app.include_router(mitre_import_router)
