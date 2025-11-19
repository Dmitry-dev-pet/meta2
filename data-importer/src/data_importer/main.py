"""
Main FastAPI application entry point for Data Importer Service.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config.settings import settings
from .config.database import get_database_adapter
from .api.endpoints.import_ import router as import_router


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Data Importer Service...")

    # Initialize database adapter
    db_adapter = get_database_adapter()

    # Create tables for development (SQLite)
    if settings.is_sqlite and settings.environment == "development":
        logger.info("Creating database tables for development...")
        await db_adapter.create_tables()

    logger.info("Data Importer Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Data Importer Service...")
    await db_adapter.close()
    logger.info("Data Importer Service stopped")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
# Data Importer Service

FastAPI service for importing and managing IT Mentor Community Platform data from Google Sheets.

## Features

- **Google Sheets Integration**: Automatic data fetching from Google Sheets
- **Smart Filtering**: Flexible filtering for students (Telegram username OR GitHub URL required)
- **Background Processing**: Asynchronous import operations with status tracking
- **Data Validation**: Comprehensive data validation and normalization
- **Database Support**: SQLite (development) and PostgreSQL (production) support

## Usage

### 1. Dry Run (Test Import)
Test data processing without database changes:
```bash
curl -X POST "http://localhost:8000/api/v1/import/dry-run"
```

### 2. Start Full Import
Begin the complete import process:
```bash
curl -X POST "http://localhost:8000/api/v1/import/start"
```

### 3. Check Import Status
Monitor background import progress:
```bash
curl -X GET "http://localhost:8000/api/v1/import/status/{import_id}"
```

## Data Model

The service processes four types of data:
- **Students**: Primary user data with Telegram and GitHub information
- **Mentors**: Mentor profiles with expertise areas
- **Projects**: Student project information
- **Reviews**: Project evaluations and feedback

## Error Handling

All endpoints include comprehensive error handling with detailed error messages and HTTP status codes.
""",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(import_router, prefix=f"{settings.api_v1_prefix}/import")


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Comprehensive health check endpoint.

    Returns service status, configuration information, and connectivity status.
    Perfect for monitoring, load balancers, and automated health checks.

    ## Response Example
    ```json
    {
        "status": "healthy",
        "service": "Data Importer Service",
        "version": "1.0.0",
        "environment": "development",
        "database": "sqlite"
    }
    ```

    ## Usage Examples
    ```bash
    # Basic health check
    curl "http://localhost:8000/health"

    # Health check with timeout (recommended for monitoring)
    curl --max-time 5 -f "http://localhost:8000/health" || echo "Service unavailable"
    ```

    ## Monitoring Integration
    This endpoint is designed for:
    - **Load balancers**: HTTP 200 response indicates service is healthy
    - **Monitoring systems**: JSON response provides detailed status
    - **Container orchestration**: Kubernetes/Docker health checks
    - **CI/CD pipelines**: Deployment verification

    ## Status Values
    - **`healthy`**: All systems operational
    - HTTP status codes:
      - **200**: Service is healthy
      - **503**: Service is unhealthy (if implemented in future)

    Returns:
        Dict containing service status, version, environment, and database type
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "database": "sqlite" if settings.is_sqlite else "postgresql",
    }


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with service information and navigation.

    Provides basic service information and navigation to key endpoints.
    Ideal for initial service discovery and verification.

    ## Response Example
    ```json
    {
        "message": "Welcome to Data Importer Service",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "api_docs": "/docs",
            "redoc": "/redoc",
            "import_api": "/api/v1/import"
        }
    }
    ```

    ## Usage Examples
    ```bash
    # Basic service info
    curl "http://localhost:8000/"

    # Check if service is running
    curl -f "http://localhost:8000/" && echo "Service is accessible"
    ```

    Returns:
        Dict containing welcome message, version, and endpoint navigation
    """
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": (
            "/docs" if settings.debug else "Documentation not available in production"
        ),
        "endpoints": {
            "health": "/health",
            "api_docs": "/docs" if settings.debug else None,
            "redoc": "/redoc" if settings.debug else None,
            "import_api": f"{settings.api_v1_prefix}/import",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
