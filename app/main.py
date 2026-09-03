from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.chat import router as chat_router
from app.api.v1.health import router as health_router
from app.container import build_container
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.telemetry import configure_telemetry

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    container = await build_container(settings)
    app.state.container = container
    try:
        yield
    finally:
        await container.close()


app = FastAPI(
    title="AI Banking Assistant",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(health_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
# Challenge-compatible alias: the brief explicitly requires POST /chat.
app.include_router(chat_router, include_in_schema=False)
configure_telemetry(
    app,
    enabled=settings.otel_enabled,
    service_name=settings.otel_service_name,
    endpoint=settings.otel_exporter_otlp_endpoint,
)
