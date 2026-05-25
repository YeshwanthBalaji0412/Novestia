from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from novestia.api.health import router as health_router
from novestia.api.v1.router import router as v1_router
from novestia.config import settings
from novestia.core.errors import register_error_handlers
from novestia.core.logging import setup_logging
from novestia.core.redis import close_redis

logger = structlog.stdlib.get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    logger.info(
        "starting",
        app=settings.app_name,
        version=settings.version,
        environment=settings.environment,
    )
    yield
    await close_redis()
    logger.info("shutting_down")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)

    app.include_router(health_router)
    app.include_router(v1_router)

    FastAPIInstrumentor.instrument_app(app)

    return app


app = create_app()
