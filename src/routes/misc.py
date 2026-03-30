"""
Miscellaneous routes for the Caching Proxy.
"""

from fastapi.responses import JSONResponse
from fastapi import APIRouter, Request, status

from ..config import settings
from ..db import redis_manager
from ..utils.logging import get_logger
from ..models import Health200Response


logger = get_logger(__name__)
router = APIRouter(tags=["Miscellaneous APIs"])


@router.get(
    path="/health",
    summary="Health check endpoint",
    description="Health check endpoint for the Caching Proxy.",
    status_code=status.HTTP_200_OK,
    response_model=Health200Response,
)
async def health(request: Request) -> JSONResponse:
    """
    Health check endpoint.

    # Args:
    - request: Request - The request object.

    # Returns:
    - JSONResponse: A JSON response containing the health status.
        - status_code: The status code of the response.
        - content: A dictionary containing the health status.
            - status: The health status of the application.
            - service: The name of the service.
            - version: The version of the service.
            - docs: The URL of the documentation.
    """

    logger.info("GET /health - Health check endpoint called")

    # Check Redis connection (handles uninitialized Redis in test/startup scenarios)
    redis_healthy = False
    try:
        redis_healthy = await redis_manager.ping()
    except RuntimeError as e:
        logger.warning(f"Redis not initialized: {e}")
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")

    overall_healthy = redis_healthy

    logger.info(
        "GET /health - Response: 200 OK - Health check endpoint completed successfully"
    )

    return JSONResponse(
        status_code=200 if overall_healthy else 503,
        content={
            "status": "healthy" if overall_healthy else "unhealthy",
            "service": settings.app_name,
            "version": settings.app_version,
            "dependencies": {
                "redis": "healthy" if redis_healthy else "unhealthy",
            },
        },
    )
