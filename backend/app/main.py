from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.db import get_db
from sqlalchemy.orm import Session

from app.api.analysis import router as analysis_router
from app.api.agent import router as agent_router
from app.api.acquisition import router as acquisition_router
from app.api.bootstrap import router as bootstrap_router
from app.api.delivery import router as delivery_router
from app.api.kernel import router as kernel_router
from app.api.meta import router as meta_router
from app.api.sources import router as sources_router
from app.api.watches import router as watches_router
from app.config import settings
from app.db import Base, engine
from app.deployment_scope import deployment_contract
from app.execution_integrity import health_contract as execution_health_contract
from app.models import (  # noqa: F401
    AnalysisRun,
    Claim,
    Event,
    ImpactReplay,
    KernelNode,
    Source,
    Watch,
)


def create_app() -> FastAPI:
    application = FastAPI(title="Research Attention OS", version="1.1.0")
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(sources_router, prefix="/sources", tags=["sources"])
    application.include_router(agent_router, prefix="/agent/v1", tags=["agent"])
    application.include_router(acquisition_router, prefix="/acquisition", tags=["acquisition"])
    application.include_router(analysis_router, prefix="/analysis", tags=["analysis"])
    application.include_router(analysis_router, prefix="/scheduler", tags=["scheduler"])
    application.include_router(kernel_router, prefix="/kernel", tags=["kernel"])
    application.include_router(bootstrap_router, prefix="/kernel", tags=["kernel"])
    application.include_router(watches_router, prefix="/watches", tags=["watches"])
    application.include_router(delivery_router, prefix="/deliveries", tags=["delivery"])
    application.include_router(meta_router, prefix="/meta", tags=["meta"])

    from app.api.sources import create_edge
    from app.schemas.api import SourceEdgeCreate

    @application.post("/source-edges")
    def source_edges(body: SourceEdgeCreate, db: Session = Depends(get_db)):
        return create_edge(body, db)

    @application.get("/media/{filename}")
    def media_asset(filename: str):
        from app.services.media_cache import cached_media_path

        path = cached_media_path(filename)
        if path is None:
            raise HTTPException(status_code=404, detail="Media asset not found")
        return FileResponse(path)

    @application.get("/health")
    def health():
        execution = execution_health_contract()
        return {
            "ok": execution.get("overall") != "BLOCKED",
            "product": "RAOS",
            "version": "1.1.0",
            "deployment": deployment_contract(),
            "execution_integrity": execution,
        }

    @application.get("/health/integrity")
    def health_integrity():
        return execution_health_contract()

    @application.get("/health/ready")
    def health_ready():
        execution = execution_health_contract()
        return {
            "ready": execution.get("overall") == "READY",
            "overall": execution.get("overall"),
            "capabilities": execution.get("capabilities"),
            "attestation": execution.get("attestation"),
        }

    return application


app = create_app()


@app.on_event("startup")
def startup() -> None:
    if settings.auto_create_tables:
        if str(settings.execution_purpose or "").upper() == "CANONICAL":
            raise RuntimeError(
                "Canonical RAOS forbids Base.metadata.create_all(); "
                "database schema authority belongs to Alembic migrations."
            )
        Base.metadata.create_all(bind=engine)
        return

    from app.schema_authority import assert_database_schema_current

    assert_database_schema_current(engine)
