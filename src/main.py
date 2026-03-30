"""
Caching Proxy - Main module for the Caching Proxy.
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db.redis_client import redis_manager
from .middleware import ProxyMiddleware
from .utils.logging import setup_logging, get_logger
from .custom_openapi import create_custom_openapi_generator
from .routes import misc_router


# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Caching Proxy...")

    # Initialize Redis connection
    logger.info("Initializing Redis connection...")
    await redis_manager.init()

    # Verify connections
    redis_connected = await redis_manager.ping()
    if redis_connected:
        logger.info("✓ Redis connection successful")
    else:
        logger.error("✗ Redis connection failed")

    logger.info(f"✓ Caching Proxy started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Caching Proxy...")

    # Close Redis connection
    await redis_manager.close()
    logger.info("✓ Redis connection closed")

    logger.info("✓ Caching Proxy shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A high‑performance caching proxy built with FastAPI and Redis.",
    contact={
        "name": "Muzaffar Shaikh",
        "email": settings.support_email,
    },
    license_info={
        "name": "MIT License",
        "url": "https://github.com/MuzaffarShaikh0201/caching-proxy/blob/main/LICENSE",
    },
    lifespan=lifespan,
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Proxy runs first on incoming requests (registered after CORS)
app.add_middleware(ProxyMiddleware)


# Add custom OpenAPI generator
doc_tags_metadata = [
    {
        "name": "Miscellaneous APIs",
        "description": "Miscellaneous APIs like health check that are not proxied to the origin.",
    },
]

app.openapi = create_custom_openapi_generator(
    app=app,
    env_config=settings,
    docs_summary="Caching Proxy API Documentation",
    docs_description=("A high‑performance caching proxy built with FastAPI and Redis."),
    docs_tags_metadata=doc_tags_metadata,
)


# Include routers
app.include_router(misc_router)
