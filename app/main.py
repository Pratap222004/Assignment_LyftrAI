import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.logging_config import setup_logging, log_request
from app.metrics import setup_metrics, get_metrics_registry
from app.storage import init_db, check_db_ready
from app.routes import router

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Setup metrics
setup_metrics()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup"""
    init_db()
    logger.info("Application started")
    yield
    logger.info("Application shutting down")


app = FastAPI(
    title="Lyftr AI Backend",
    description="Backend API with webhook handling and message management",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all requests in JSON format"""
    import time
    request.state.start_time = time.time()
    response = await call_next(request)
    log_request(request, response)
    return response

# Include routers
app.include_router(router)


@app.get("/metrics")
async def metrics():
    """Prometheus-style metrics endpoint"""
    return Response(
        content=generate_latest(get_metrics_registry()),
        media_type=CONTENT_TYPE_LATEST
    )

