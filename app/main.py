"""FastAPI application entry point.

This is the main entry point for the Plex MediaProvider application. It:
1. Configures structured logging (JSON or console based on debug mode)
2. Sets up the FastAPI application with CORS middleware
3. Defines the application lifecycle (startup/shutdown)
4. Registers API route handlers for TV and Movie providers
5. Runs the app on specified host/port
"""

import uvicorn
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routes import movie, tv
from app.web.router import router as admin_router

# ===== LOGGING CONFIGURATION =====
# Set up structured logging using structlog library
# This creates more informative, machine-readable logs with context
structlog.configure(
    processors=[
        # Filter logs by level (debug, info, error, etc.)
        structlog.stdlib.filter_by_level,
        # Add the logger name to each log entry
        structlog.stdlib.add_logger_name,
        # Add the log level (DEBUG, INFO, ERROR, etc.)
        structlog.stdlib.add_log_level,
        # Convert positional arguments to a more readable format
        structlog.stdlib.PositionalArgumentsFormatter(),
        # Add ISO-formatted timestamp to each log
        structlog.processors.TimeStamper(fmt="iso"),
        # Include stack traces if present
        structlog.processors.StackInfoRenderer(),
        # Format exception information
        structlog.processors.format_exc_info,
        # Decode any unicode strings
        structlog.processors.UnicodeDecoder(),
        # Use human-readable console output in debug mode, JSON output in production
        structlog.dev.ConsoleRenderer() if get_settings().debug else structlog.processors.JSONRenderer(),
    ],
    # Use BoundLogger for contextual logging
    wrapper_class=structlog.stdlib.BoundLogger,
    # Use regular dicts for context (instead of OrderedDict)
    context_class=dict,
    # Use the standard library logger factory
    logger_factory=structlog.stdlib.LoggerFactory(),
    # Cache logger instances after first use for performance
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


# ===== APPLICATION LIFECYCLE MANAGEMENT =====
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown events.

    This function is called when the application starts and stops.
    It initializes the database on startup and logs shutdown on exit.
    """
    settings = get_settings()
    logger.info(
        "Starting ThePornDB Plex Provider",
        host=settings.provider_host,
        port=settings.provider_port,
        debug=settings.debug,
    )

    # Initialize database connection and create tables if they don't exist
    from app.db.database import init_db
    await init_db()

    # Code after 'yield' runs on shutdown
    yield

    # Cleanup code - log that we're shutting down
    logger.info("Shutting down ThePornDB Plex Provider")


# ===== FASTAPI APPLICATION FACTORY =====
def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    This factory function:
    1. Creates a FastAPI instance with metadata
    2. Adds CORS middleware to allow cross-origin requests
    3. Registers route handlers for TV and Movie providers
    4. Includes the admin router
    5. Adds a health check endpoint

    Returns:
        FastAPI: Configured application instance
    """
    settings = get_settings()

    # Create the FastAPI application with metadata used in OpenAPI/Swagger docs
    app = FastAPI(
        title=settings.app_name,
        description="Plex Media Provider for ThePornDB",
        version="1.0.0",
        lifespan=lifespan,  # Set the lifespan context manager
        # Only show API docs in debug mode
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # ===== MIDDLEWARE SETUP =====
    # Add CORS (Cross-Origin Resource Sharing) middleware
    # This allows the Plex server to make requests to this provider from different origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow requests from any origin
        allow_credentials=True,  # Allow cookies/credentials in requests
        allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
        allow_headers=["*"],  # Allow all headers
    )

    # ===== ROUTE REGISTRATION =====
    # Register the TV provider routes at /tv prefix
    # Handles: show matching, scene matching, metadata retrieval
    app.include_router(tv.router, prefix="/tv", tags=["TV Provider"])

    # Register the Movie provider routes at /movie prefix
    # Handles: movie matching and metadata retrieval
    app.include_router(movie.router, prefix="/movie", tags=["Movie Provider"])

    # Register the admin UI routes at /admin prefix
    # Handles: cache management, search, dashboard
    app.include_router(admin_router, prefix="/admin", tags=["Admin"])

    # ===== HEALTH CHECK ENDPOINT =====
    # Simple endpoint that returns HTTP 200 OK when the service is running
    # Useful for container orchestration (Docker, Kubernetes) health checks
    @app.get("/health", tags=["Health"])
    async def health_check() -> dict[str, str]:
        """Health check endpoint for service monitoring.

        Returns:
            Dict with status and service name
        """
        return {"status": "healthy", "service": "tpdb-plex-provider"}

    return app


# ===== APPLICATION INSTANCE =====
# Create the app instance once when the module is imported
app = create_app()


# ===== STARTUP FUNCTION =====
def run() -> None:
    """Run the application using uvicorn ASGI server.

    This starts the HTTP server on the configured host and port,
    with auto-reload in debug mode and appropriate logging level.
    """
    settings = get_settings()
    uvicorn.run(
        "app.main:app",  # Module and app instance to run
        host=settings.provider_host,  # IP address to bind to
        port=settings.provider_port,  # Port to listen on
        reload=settings.debug,  # Auto-reload on code changes in debug mode
        log_level="debug" if settings.debug else "info",  # Logging verbosity
    )


# ===== ENTRY POINT =====
if __name__ == "__main__":
    run()
