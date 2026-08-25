from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import get_db
from sqlalchemy.orm import Session

from app.api.analysis import router as analysis_router
from app.api.kernel import router as kernel_router
from app.api.meta import router as meta_router
from app.api.sources import router as sources_router
from app.api.watches import router as watches_router
from app.config import settings
from app.db import Base, engine
from app.models import (  # noqa: F401
    Claim,
    Event,
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
    application.include_router(analysis_router, prefix="/analysis", tags=["analysis"])
    application.include_router(analysis_router, prefix="/scheduler", tags=["scheduler"])
    application.include_router(kernel_router, prefix="/kernel", tags=["kernel"])
    application.include_router(watches_router, prefix="/watches", tags=["watches"])
    application.include_router(meta_router, prefix="/meta", tags=["meta"])

    from app.api.sources import create_edge
    from app.schemas.api import SourceEdgeCreate

    @application.post("/source-edges")
    def source_edges(body: SourceEdgeCreate, db: Session = Depends(get_db)):
        return create_edge(body, db)

    @application.get("/health")
    def health():
        return {"ok": True, "product": "RAOS", "version": "1.1.0"}

    return application


app = create_app()


@app.on_event("startup")
def startup() -> None:
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
