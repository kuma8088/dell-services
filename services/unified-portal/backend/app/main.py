"""Main FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.config import get_settings
from app.database import Base, engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan management.

    Args:
        app: FastAPI application instance.

    Yields:
        None
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Unified management portal for Blog System and Mailserver",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint for Docker healthcheck and monitoring.

    Returns:
        JSONResponse: Health status.
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "service": settings.app_name,
            "version": settings.app_version,
        },
        status_code=200,
    )


# Root endpoint
@app.get("/")
async def root() -> JSONResponse:
    """Root endpoint - API information.

    Returns:
        JSONResponse: API information.
    """
    return JSONResponse(
        content={
            "service": settings.app_name,
            "version": settings.app_version,
            "status": "running",
            "docs": "/docs",
            "health": "/health",
        },
        status_code=200,
    )


# Import and register routers
# from app.routers import auth, dashboard, docker, backup, websocket
# app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
# app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
# app.include_router(docker.router, prefix="/api/v1/docker", tags=["Docker"])
# app.include_router(backup.router, prefix="/api/v1/backup", tags=["Backup"])
# app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
