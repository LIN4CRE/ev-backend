"""Application entrypoint for the Ev backend."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.admin import router as admin_router
from app.api.routes.alexa import router as alexa_router
from app.api.routes.alexa_improved import router as alexa_improved_router
from app.api.routes.chat import router as chat_router
from app.api.routes.downloads import router as downloads_router
from app.api.routes.evbot import router as evbot_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.request_logging import RequestLoggingMiddleware
from app.services.memory_service import close_memory_provider
from app.services.startup_service import StartupService

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run application startup and shutdown hooks."""
    startup_service = StartupService(settings)
    logger.info("application_starting", app_name=settings.app_name, environment=settings.environment)
    startup_service.emit_startup_report()
    yield
    logger.info("application_stopping", app_name=settings.app_name, environment=settings.environment)
    close_memory_provider()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

register_exception_handlers(app)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix=settings.api_v1_prefix)
app.include_router(alexa_router, prefix=settings.api_v1_prefix)
app.include_router(alexa_improved_router, prefix=settings.api_v1_prefix)
app.include_router(chat_router, prefix=settings.api_v1_prefix)
app.include_router(admin_router, prefix=settings.api_v1_prefix)
app.include_router(evbot_router, prefix=settings.api_v1_prefix)
app.include_router(downloads_router)

# Static files (serves the OP Agent panel at /static/panel.html).
# StaticFiles uses aiofiles under the hood — ensure it is in requirements.txt.
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/panel")
async def panel() -> FileResponse:
    """Serve the OP Agent control panel HTML."""
    return FileResponse("app/static/panel.html")


@app.get("/")
async def root() -> FileResponse:
    """Serve the EV-Bot Setup Dashboard."""
    return FileResponse("app/static/setup.html")

