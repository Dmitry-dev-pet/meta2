"""
Google Sheets API client for data import.
"""

import json
from typing import List, Dict, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from ..config.settings import settings
import structlog

logger = structlog.get_logger(__name__)


class GoogleSheetsClient:
    """Client for accessing Google Sheets API."""

    def __init__(self):
        """Initialize Google Sheets client."""
        self.service = None
        self._credentials = None

    async def initialize(self) -> None:
        """Initialize the Google Sheets service."""
        try:
            # Load service account credentials
            self._credentials = service_account.Credentials.from_service_account_file(
                settings.google_sheets_credentials_path,
                scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
            )

            # Build the service
            self.service = build("sheets", "v4", credentials=self._credentials)
            logger.info("Google Sheets client initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize Google Sheets client", error=str(e))
            raise

    async def fetch_sheet_data(
        self,
        spreadsheet_id: str,
        range_name: str,
    ) -> List[List[str]]:
        """
        Fetch data from a specific sheet range.

        Args:
            spreadsheet_id: The ID of the spreadsheet
            range_name: The range to fetch (e.g., "Sheet1!A2:C")

        Returns:
            List of rows, where each row is a list of cell values
        """
        if not self.service:
            await self.initialize()

        try:
            logger.info(
                "Fetching data from Google Sheets",
                spreadsheet_id=spreadsheet_id,
                range=range_name,
            )

            result = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=range_name)
                .execute()
            )

            values = result.get("values", [])
            logger.info(
                "Successfully fetched data from Google Sheets",
                rows_count=len(values),
                spreadsheet_id=spreadsheet_id,
                range=range_name,
            )

            return values

        except HttpError as e:
            logger.error(
                "Google Sheets API error",
                error=str(e),
                spreadsheet_id=spreadsheet_id,
                range=range_name,
            )
            raise

        except Exception as e:
            logger.error(
                "Unexpected error fetching Google Sheets data",
                error=str(e),
                spreadsheet_id=spreadsheet_id,
                range=range_name,
            )
            raise

    async def fetch_students_data(self) -> List[List[str]]:
        """Fetch students data from the main spreadsheet."""
        return await self.fetch_sheet_data(
            spreadsheet_id=settings.main_spreadsheet_id,
            range_name=settings.students_range,
        )

    async def fetch_projects_data(self) -> List[List[str]]:
        """Fetch projects data from the main spreadsheet."""
        return await self.fetch_sheet_data(
            spreadsheet_id=settings.main_spreadsheet_id,
            range_name=settings.projects_range,
        )

    async def fetch_reviews_data(self) -> List[List[str]]:
        """Fetch reviews data from the main spreadsheet."""
        return await self.fetch_sheet_data(
            spreadsheet_id=settings.main_spreadsheet_id,
            range_name=settings.reviews_range,
        )

    async def fetch_mentors_data(self) -> List[List[str]]:
        """Fetch mentors data from the mentors spreadsheet."""
        return await self.fetch_sheet_data(
            spreadsheet_id=settings.mentors_spreadsheet_id,
            range_name=settings.mentors_range,
        )

    async def fetch_sponsored_reviews_data(self) -> List[List[str]]:
        """Fetch sponsored reviews data from the main spreadsheet."""
        return await self.fetch_sheet_data(
            spreadsheet_id=settings.main_spreadsheet_id,
            range_name=settings.sponsored_reviews_range,
        )

    async def fetch_all_data(self) -> Dict[str, List[List[str]]]:
        """Fetch all data from all spreadsheets in parallel."""
        logger.info("Starting to fetch all data from Google Sheets")

        try:
            # Import here to avoid circular imports in production
            import asyncio

            # Fetch all data concurrently
            tasks = [
                self.fetch_students_data(),
                self.fetch_projects_data(),
                self.fetch_reviews_data(),
                self.fetch_mentors_data(),
            ]

            # Add sponsored reviews if enabled
            if settings.enable_financial_import:
                tasks.append(self.fetch_sponsored_reviews_data())

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Unpack results
            students_data, projects_data, reviews_data, mentors_data = results[:4]
            sponsored_reviews_data = (
                results[4] if settings.enable_financial_import else []
            )

            # Check for exceptions
            data_sources: Dict[str, List[List[str]] | BaseException] = {
                "students": students_data,
                "projects": projects_data,
                "reviews": reviews_data,
                "mentors": mentors_data,
            }

            # Add sponsored reviews if enabled
            if settings.enable_financial_import:
                data_sources["sponsored_reviews"] = sponsored_reviews_data

            cleaned: Dict[str, List[List[str]]] = {}
            for source, data in data_sources.items():
                if isinstance(data, BaseException):
                    logger.error(f"Failed to fetch {source} data", error=str(data))
                    cleaned[source] = []
                else:
                    logger.info(f"Successfully fetched {source} data", rows=len(data))
                    cleaned[source] = data

            return cleaned

        except Exception as e:
            logger.error("Error fetching all data", error=str(e))
            raise

    async def save_raw_data(
        self, data: Dict[str, List[List[str]]], filename: str = "import_raw.json"
    ) -> None:
        """Save raw data to file for debugging purposes."""
        try:
            from datetime import datetime
            import os

            # Ensure backup directory exists
            os.makedirs(settings.backup_dir, exist_ok=True)

            # Prepare data with metadata
            raw_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "spreadsheet_ids": {
                    "main": settings.main_spreadsheet_id,
                    "mentors": settings.mentors_spreadsheet_id,
                },
                "data": data,
            }

            # Save to file
            filepath = os.path.join(settings.backup_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(raw_data, f, ensure_ascii=False, indent=2)

            logger.info(
                "Raw data saved to file",
                filepath=filepath,
                total_rows=sum(len(rows) for rows in data.values()),
            )

        except Exception as e:
            logger.error("Error saving raw data", error=str(e))
            # Don't raise here - this is not critical for the import process


# Global client instance
_google_sheets_client: Optional[GoogleSheetsClient] = None


def get_google_sheets_client() -> GoogleSheetsClient:
    """Get or create Google Sheets client instance."""
    global _google_sheets_client
    if _google_sheets_client is None:
        _google_sheets_client = GoogleSheetsClient()
    return _google_sheets_client
