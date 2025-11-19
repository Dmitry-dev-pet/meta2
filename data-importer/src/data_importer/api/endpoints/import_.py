"""
Import API endpoints.
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any
from pydantic import BaseModel, Field

from ...services.import_service import ImportService
from ...services.google_sheets import get_google_sheets_client
from structlog import get_logger

logger = get_logger(__name__)

router = APIRouter()


class ImportResponse(BaseModel):
    """Response model for import operations."""

    message: str = Field(..., description="Status message")
    import_id: str = Field(..., description="Unique import ID")
    status: str = Field(..., description="Import status")
    statistics: Dict[str, Any] = Field(
        default_factory=dict, description="Import statistics"
    )


class ImportStatus(BaseModel):
    """Model for import status."""

    status: str = Field(..., description="Current status")
    message: str = Field(..., description="Status message")
    progress: Dict[str, Any] = Field(
        default_factory=dict, description="Progress information"
    )


# Global import service instance
import_service = ImportService()

# Store for background tasks (in production, use Redis or similar)
background_imports: Dict[str, Dict[str, Any]] = {}


@router.post("/start", response_model=ImportResponse, status_code=202)
async def start_import(background_tasks: BackgroundTasks) -> ImportResponse:
    """
    Start data import from Google Sheets.

    This endpoint initiates the complete data import process that runs in the background.
    The process includes three main stages:
    1. **Data Fetching**: Retrieves student, mentor, project, and review data from Google Sheets
    2. **Data Processing**: Applies validation, filtering, and normalization rules
    3. **Database Import**: Stores processed data in the database with proper relationships

    **Filtering Logic**: Students are imported if they have EITHER a Telegram username OR GitHub URL.
    This flexible approach ensures maximum data capture while maintaining quality standards.

    ## Response Example
    ```json
    {
        "message": "Import process started successfully",
        "import_id": "import_1699912345678",
        "status": "started",
        "statistics": {}
    }
    ```

    ## Next Steps
    Use the returned `import_id` to monitor progress:
    ```bash
    curl -X GET "http://localhost:8000/api/v1/import/status/import_1699912345678"
    ```

    ## Processing Time
    - Small datasets (< 100 records): ~10-30 seconds
    - Medium datasets (100-500 records): ~30-60 seconds
    - Large datasets (> 500 records): ~1-3 minutes
    """
    try:
        logger.info("Starting data import request")

        # Generate unique import ID
        import_id = f"import_{int(datetime.now().timestamp() * 1000)}"

        # Initialize background task status
        background_imports[import_id] = {
            "status": "started",
            "message": "Import process started",
            "progress": {},
            "started_at": datetime.now().isoformat(),
        }

        # Add background task
        background_tasks.add_task(run_import_background, import_id)

        logger.info("Import task started", import_id=import_id)

        return ImportResponse(
            message="Import process started successfully",
            import_id=import_id,
            status="started",
        )

    except Exception as e:
        logger.error("Failed to start import", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start import: {str(e)}")


@router.get("/status/{import_id}", response_model=ImportStatus)
async def get_import_status(import_id: str) -> ImportStatus:
    """
    Get the status of an import process.

    Monitor the progress of a background import operation using the unique import ID
    returned by the `/start` endpoint.

    ## Status Values
    - **`started`**: Import task has been queued and will begin processing
    - **`fetching_data`**: Currently retrieving data from Google Sheets
    - **`processing`**: Data validation and filtering in progress
    - **`importing`**: Writing processed data to database
    - **`completed`**: Import finished successfully
    - **`failed`**: Import encountered an error (check error details)

    ## Response Example
    ```json
    {
        "status": "processing",
        "message": "Processing student data...",
        "progress": {
            "stage": "data_validation",
            "students_processed": 250,
            "total_students": 500,
            "progress_percentage": 50
        }
    }
    ```

    ## Usage Example
    ```bash
    curl -X GET "http://localhost:8000/api/v1/import/status/import_1699912345678"
    ```

    ## Error Cases
    - **404**: Import ID not found or expired
    - **500**: Server error during status retrieval

    Args:
        import_id: The unique identifier returned by the `/start` endpoint

    Returns:
        Current status, progress information, and any error details if applicable
    """
    if import_id not in background_imports:
        raise HTTPException(status_code=404, detail="Import process not found")

    import_status = background_imports[import_id]

    return ImportStatus(
        status=import_status["status"],
        message=import_status["message"],
        progress=import_status.get("progress", {}),
    )


@router.post("/dry-run")
async def dry_run_import() -> Dict[str, Any]:
    """
    Perform a dry run of the import process.

    Test the complete data processing pipeline without making any database changes.
    This endpoint is perfect for validating data quality, testing filtering logic,
    and estimating processing time before running a full import.

    ## What Gets Processed
    - **Data Fetching**: Retrieves current data from Google Sheets
    - **Validation**: Checks data format and required fields
    - **Filtering**: Applies student eligibility rules (Telegram OR GitHub requirement)
    - **Normalization**: Cleans and standardizes data formats
    - **Statistics**: Generates detailed reports about data quality

    ## Filtering Rules Applied
    - Students must have EITHER Telegram username OR GitHub URL
    - Invalid or empty records are filtered out
    - Duplicate data is identified and reported
    - Data quality metrics are calculated

    ## Response Example
    ```json
    {
        "message": "Dry run completed successfully",
        "statistics": {
            "raw_records": {
                "students": 600,
                "mentors": 25,
                "projects": 450,
                "reviews": 800,
                "sponsored_reviews": 50
            },
            "processed_records": {
                "students": 544,
                "mentors": 25,
                "projects": 450,
                "reviews": 800,
                "sponsored_reviews": 48
            },
            "filtered_records": {
                "students": 56,
                "sponsored_reviews": 2,
                "reasons": {
                    "students": {
                        "no_telegram_or_github": 45,
                        "invalid_format": 8,
                        "duplicates": 3
                    },
                    "sponsored_reviews": {
                        "validation_errors": 2
                    }
                }
            }
        },
        "processed_data": {
            "students": 544,
            "mentors": 25,
            "projects": 450,
            "reviews": 800,
            "sponsored_reviews": 48
        }
    }
    ```

    ## Usage Examples
    ```bash
    # Basic dry run
    curl -X POST "http://localhost:8000/api/v1/import/dry-run"

    # Save results to file
    curl -X POST "http://localhost:8000/api/v1/import/dry-run" | jq . > dry-run-results.json
    ```

    ## Common Use Cases
    - **Pre-import validation**: Check data quality before full import
    - **Filtering testing**: Verify filtering logic is working correctly
    - **Data audit**: Understand what data will be imported
    - **Troubleshooting**: Identify data issues before production import
    - **Performance estimation**: Get baseline for processing times

    ## Benefits
    - Zero database impact
    - Comprehensive data quality report
    - Filtering effectiveness analysis
    - Performance benchmarking
    - Error identification without risk
    """
    try:
        logger.info("Starting dry run import")

        # Get Google Sheets client and fetch data
        google_sheets_client = get_google_sheets_client()
        raw_data = await google_sheets_client.fetch_all_data()

        # Process data without database import
        from ...services.data_processor import DataProcessor

        processor = DataProcessor()
        processed_result = await processor.process_all_data(raw_data)

        logger.info("Dry run completed successfully")

        return {
            "message": "Dry run completed successfully",
            "statistics": processed_result["statistics"],
            "processed_data": {
                "students": len(processed_result["processed_data"]["students"]),
                "mentors": len(processed_result["processed_data"]["mentors"]),
                "projects": len(processed_result["processed_data"]["projects"]),
                "reviews": len(processed_result["processed_data"]["reviews"]),
                "sponsored_reviews": len(
                    processed_result["processed_data"].get("sponsored_reviews", [])
                ),
            },
        }

    except Exception as e:
        logger.error("Dry run failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Dry run failed: {str(e)}")


async def run_import_background(import_id: str) -> None:
    """Run actual data import in background."""
    try:
        # Fetching stage
        background_imports[import_id]["status"] = "fetching_data"
        background_imports[import_id]["message"] = "Fetching data from Google Sheets"

        # Run real import
        logger.info("Starting real import", import_id=import_id)
        result = await import_service.run_full_import()

        # Completed
        background_imports[import_id]["status"] = "completed"
        background_imports[import_id]["message"] = "Import finished successfully"
        background_imports[import_id]["progress"] = result

        logger.info("Import completed successfully", import_id=import_id, result=result)

    except Exception as e:
        background_imports[import_id]["status"] = "failed"
        background_imports[import_id]["message"] = f"Import failed: {e}"
        logger.error("Import failed", import_id=import_id, error=str(e))
