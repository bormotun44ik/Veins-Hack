import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# App-level logging — INFO by default так чтобы видеть bg-regen и другие наши сигналы
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("app").setLevel(logging.INFO)

app = FastAPI(title="Veins", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r".*",  # demo mode — открыть для всех (LAN demo)
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def veins_error_handler(request: Request, exc: Exception):
    from app.errors import VeinsError
    if isinstance(exc, VeinsError):
        return JSONResponse(status_code=exc.http_status,
                            content={"error": {"code": exc.code, "message": str(exc)}})
    return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_ERROR", "message": str(exc)}})

@app.on_event("startup")
async def startup():
    from app.db import init_db, get_connection
    init_db()
    conn = get_connection()
    try:
        from app.ingest import ingest_all
        ingest_all(conn)
    except ImportError:
        pass
    try:
        from app.signals.composite import update_all_people
        update_all_people(conn)
    except ImportError:
        pass
    try:
        from app.llm.smart_cache import init_smart_cache
        init_smart_cache(conn)
    except Exception:
        pass

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}

# Graph router
from app.graph.api import router as graph_router
app.include_router(graph_router)

# LLM router (optional)
try:
    from app.llm.api import router as llm_router
    app.include_router(llm_router)
except ImportError:
    pass

# Dashboard router (phase 2 — Agent H)
try:
    from app.dashboard.api import router as dashboard_router
    app.include_router(dashboard_router)
except ImportError:
    pass

# Ingest API router (phase 2 — Agent J)
try:
    from app.ingest.api import router as ingest_api_router
    app.include_router(ingest_api_router)
except ImportError:
    pass
