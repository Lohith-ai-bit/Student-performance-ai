"""FastAPI application entry point."""
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Make the shared `ml` package importable (backend and ml live side by side).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.api.routes import api_router  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.errors import register_exception_handlers  # noqa: E402
from app.core.security_middleware import (  # noqa: E402
    RateLimitMiddleware, SecurityHeadersMiddleware,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm up baseline artifacts at startup so problems are visible in logs immediately.
    # Torch models load lazily on first advanced prediction (they are heavyweight).
    try:
        from ml.inference.predictor import PerformancePredictor

        predictor = PerformancePredictor()
        print(f"[startup] Baseline artifacts loaded: {predictor.model_name} v{predictor.model_version}")
    except FileNotFoundError as exc:
        print(f"[startup] WARNING: {exc}")
    print("[startup] Transformer/Hybrid models will load lazily on first use")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    description=(
        "Hybrid ML + Transformer framework for student performance prediction, "
        "explainable AI (SHAP/LIME) and personalized learning recommendations."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "app": settings.APP_NAME}
