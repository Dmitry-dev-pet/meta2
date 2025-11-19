"""
Data processing service for importing Google Sheets data.
"""

import json
from datetime import datetime
from typing import Dict, List, Any, cast
from ..config.settings import settings
from ..utils.validation import (
    normalize_telegram_username,
    normalize_github_url,
    parse_period,
    validate_row_length,
    clean_and_validate,
)
from structlog import get_logger

logger = get_logger(__name__)


class DataProcessor:
    """Service for processing Google Sheets data with Telegram filtering."""

    def __init__(self):
        """Initialize the data processor."""
        self.processed_data = {
            "students": [],
            "mentors": [],
            "projects": [],
            "reviews": [],
            "sponsored_reviews": [],  # Add sponsored reviews
        }
        self.statistics = {
            "students": {"total": 0, "passed_filter": 0, "imported": 0},
            "mentors": {"total": 0, "passed_filter": 0, "imported": 0},
            "projects": {"total": 0, "imported": 0, "linking_errors": 0},
            "reviews": {"total": 0, "imported": 0, "linking_errors": 0},
            "sponsored_reviews": {
                "total": 0,
                "imported": 0,
                "linking_errors": 0,
                "validation_errors": 0,
            },
        }

    async def process_all_data(
        self, raw_data: Dict[str, List[List[str]]]
    ) -> Dict[str, Any]:
        """
        Process all raw data from Google Sheets.

        Args:
            raw_data: Raw data from Google Sheets

        Returns:
            Processed data with statistics
        """
        logger.info("Starting data processing")

        # Process each data type
        self.processed_data["students"] = await self._process_students(
            raw_data.get("students", [])
        )
        self.processed_data["mentors"] = await self._process_mentors(
            raw_data.get("mentors", [])
        )
        self.processed_data["projects"] = await self._process_projects(
            raw_data.get("projects", [])
        )
        self.processed_data["reviews"] = await self._process_reviews(
            raw_data.get("reviews", [])
        )

        # Process sponsored reviews if enabled and data is available
        if settings.enable_financial_import and "sponsored_reviews" in raw_data:
            self.processed_data["sponsored_reviews"] = (
                await self._process_sponsored_reviews(
                    raw_data.get("sponsored_reviews", [])
                )
            )

        # Prepare result
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "processed_data": self.processed_data,
            "statistics": self.statistics,
        }

        # Save processed data for debugging
        await self._save_processed_data(result)

        logger.info(
            "Data processing completed",
            total_students=self.statistics["students"]["passed_filter"],
            total_mentors=self.statistics["mentors"]["passed_filter"],
            total_projects=len(self.processed_data["projects"]),
            total_reviews=len(self.processed_data["reviews"]),
            total_sponsored_reviews=len(
                self.processed_data.get("sponsored_reviews", [])
            ),
        )

        return result

    async def _process_students(
        self, students_data: List[List[str]]
    ) -> List[Dict[str, Any]]:
        """Process students data with Telegram filtering."""
        logger.info("Processing students data", total_rows=len(students_data))
        self.statistics["students"]["total"] = len(students_data)

        processed_students = []

        for row in students_data:
            if not validate_row_length(row, 1, "student"):
                continue

            # Define field validators
            field_validators = {
                "github_url": (0, normalize_github_url),
                "telegram_user_id": (
                    1,
                    lambda x: int(x) if x and x.isdigit() else None,
                ),
                "telegram_username": (2, normalize_telegram_username),
            }

            # Clean and validate data
            student_data = clean_and_validate(row, field_validators)

            # Apply Telegram filtering
            if not self._filter_student(student_data):
                continue

            processed_students.append(
                {
                    "github_url": student_data["github_url"],
                    "telegram_user_id": student_data["telegram_user_id"],
                    "telegram_username": student_data["telegram_username"],
                    "role": "STUDENT",
                }
            )

        self.statistics["students"]["passed_filter"] = len(processed_students)
        logger.info("Students processed", passed_filter=len(processed_students))

        return processed_students

    async def _process_mentors(
        self, mentors_data: List[List[str]]
    ) -> List[Dict[str, Any]]:
        """Process mentors data with Telegram filtering."""
        logger.info("Processing mentors data", total_rows=len(mentors_data))
        self.statistics["mentors"]["total"] = len(mentors_data)

        processed_mentors = []

        for row in mentors_data:
            if not validate_row_length(row, 4, "mentor"):
                continue

            # Define field validators for mentors (A-H columns)
            field_validators = {
                "github_url": (0, normalize_github_url),  # Column A: GitHub URL
                "full_name": (
                    2,
                    lambda x: x.strip() if x else "",
                ),  # Column C: Full Name (Column B contains sequence numbers, not telegram_user_id)
                "telegram_username": (
                    3,
                    normalize_telegram_username,
                ),  # Column D: Telegram Username
                "languages": (
                    4,
                    lambda x: x.strip() if x else "",
                ),  # Column E: Languages
                "services": (5, lambda x: x.strip() if x else ""),  # Column F: Services
                "price_type": (
                    6,
                    lambda x: x.strip() if x else "",
                ),  # Column G: Price Type
                "website_url": (
                    7,
                    lambda x: x.strip() if x else "",
                ),  # Column H: Website URL
            }

            # Clean and validate data
            mentor_data = clean_and_validate(row, field_validators)

            # Apply Telegram filtering (only Telegram required for mentors)
            if not self._filter_mentor(mentor_data):
                continue

            processed_mentors.append(
                {
                    "telegram_username": mentor_data["telegram_username"],
                    "telegram_user_id": None,  # Mentors don't have telegram_user_id in Google Sheets
                    "github_url": mentor_data[
                        "github_url"
                    ],  # Use GitHub URL from column A
                    "role": "MENTOR",
                    "profile": {
                        "full_name": mentor_data["full_name"],
                        "languages": mentor_data["languages"],
                        "services": mentor_data["services"],
                        "price_type": mentor_data["price_type"],
                        "website_url": mentor_data["website_url"],
                    },
                }
            )

        self.statistics["mentors"]["passed_filter"] = len(processed_mentors)
        logger.info("Mentors processed", passed_filter=len(processed_mentors))

        return processed_mentors

    async def _process_projects(
        self, projects_data: List[List[str]]
    ) -> List[Dict[str, Any]]:
        """Process projects data with period handling."""
        logger.info("Processing projects data", total_rows=len(projects_data))
        self.statistics["projects"]["total"] = len(projects_data)

        processed_projects = []
        current_period = None

        for row in projects_data:
            # Handle period headers (every other row according to architecture)
            if len(row) <= 2 or (len(row) > 1 and not row[1].strip()):
                current_period = parse_period(row[0]) if row and row[0] else None
                continue

            if not validate_row_length(row, 8, "project"):
                continue

            # Define field validators
            field_validators = {
                "name": (1, lambda x: x.strip() if x else None),
                "language": (2, lambda x: x.strip() if x else ""),
                "repository_url": (4, lambda x: x.strip() if x else ""),
                "author_github_url": (6, normalize_github_url),
            }

            # Clean and validate data
            project_data = clean_and_validate(row, field_validators)

            # Apply filtering (name and author GitHub URL required)
            if not self._filter_project(project_data):
                continue

            processed_projects.append(
                {
                    "name": project_data["name"],
                    "language": project_data["language"],
                    "repository_url": project_data["repository_url"],
                    "author_github_url": project_data["author_github_url"],
                    "submission_date": current_period,
                }
            )

        self.statistics["projects"]["imported"] = len(processed_projects)
        logger.info("Projects processed", imported=len(processed_projects))

        return processed_projects

    async def _process_reviews(
        self, reviews_data: List[List[str]]
    ) -> List[Dict[str, Any]]:
        """Process reviews data."""
        logger.info("Processing reviews data", total_rows=len(reviews_data))
        self.statistics["reviews"]["total"] = len(reviews_data)

        processed_reviews = []

        for row in reviews_data:
            if not validate_row_length(row, 8, "review"):
                continue

            # Define field validators
            field_validators = {
                "project_name": (
                    1,
                    lambda x: x.strip() if x else None,
                ),  # Column B: Project name
                "mentor_telegram": (
                    7,
                    normalize_telegram_username,
                ),  # Column H: Mentor telegram
                "period_date": (0, parse_period),  # Column A: Period date
                "review_type": (
                    4,
                    lambda x: x.strip() if x else "",
                ),  # Column E: Review type
                "review_url": (
                    5,
                    lambda x: x.strip() if x else "",
                ),  # Column F: Review URL
                "repository_url": (
                    3,
                    lambda x: x.strip() if x else "",
                ),  # Column D: Repository URL (kept for reference)
            }

            # Clean and validate data
            review_data = clean_and_validate(row, field_validators)

            # Apply filtering (project and mentor required)
            if not self._filter_review(review_data):
                continue

            processed_reviews.append(
                {
                    "project_name": review_data[
                        "project_name"
                    ],  # Use project name for linking
                    "mentor_telegram": review_data["mentor_telegram"],
                    "repository_url": review_data[
                        "repository_url"
                    ],  # Keep for reference/debugging
                    "period_date": review_data["period_date"],
                    "review_type": review_data["review_type"],
                    "review_url": review_data["review_url"],
                }
            )

        self.statistics["reviews"]["imported"] = len(processed_reviews)
        logger.info("Reviews processed", imported=len(processed_reviews))

        return processed_reviews

    def _filter_student(self, student_data: Dict[str, Any]) -> bool:
        """Apply flexible filtering to student data."""
        # Students must have either GitHub URL OR Telegram username
        github_url = student_data.get("github_url")
        telegram_username = student_data.get("telegram_username")

        if not github_url and not telegram_username:
            logger.warning(
                "Student filtered out - no identifiers",
                github_url=github_url,
                telegram_username=telegram_username,
                raw_data=student_data,
            )
            return False

        logger.debug(
            "Student passed filter",
            github_url=github_url,
            telegram_username=telegram_username,
        )
        return True

    def _filter_mentor(self, mentor_data: Dict[str, Any]) -> bool:
        """Apply Telegram filtering to mentor data."""
        # Mentors must have Telegram username (GitHub is optional)
        telegram_username = mentor_data.get("telegram_username")

        if not telegram_username:
            logger.warning(
                "Mentor filtered out - no telegram username",
                telegram_username=telegram_username,
                github_url=mentor_data.get("github_url"),
                raw_data=mentor_data,
            )
            return False

        logger.debug(
            "Mentor passed filter",
            telegram_username=telegram_username,
            github_url=mentor_data.get("github_url"),
        )
        return True

    def _filter_project(self, project_data: Dict[str, Any]) -> bool:
        """Apply filtering to project data."""
        # Projects must have name and author GitHub URL
        if not project_data.get("name") or not project_data.get("author_github_url"):
            return False
        return True

    def _filter_review(self, review_data: Dict[str, Any]) -> bool:
        """Apply filtering to review data."""
        # Reviews must have mentor telegram and either project name or author github url
        if not review_data.get("mentor_telegram"):
            return False
        # Allow if either project name or author github url is present
        if not review_data.get("project_name") and not review_data.get(
            "author_github_url"
        ):
            return False
        return True

    async def _save_processed_data(self, result: Dict[str, Any]) -> None:
        """Save processed data to file for debugging."""
        try:
            import os
            from datetime import date

            def json_serializer(obj):
                """JSON serializer for objects not serializable by default json code"""
                if isinstance(obj, date):
                    return obj.isoformat()
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

            # Ensure backup directory exists
            os.makedirs(settings.backup_dir, exist_ok=True)

            # Save to file
            filepath = os.path.join(settings.backup_dir, "import_processed.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(
                    result, f, ensure_ascii=False, indent=2, default=json_serializer
                )

            logger.info("Processed data saved", filepath=filepath)

        except Exception as e:
            logger.error("Error saving processed data", error=str(e))

    async def _process_sponsored_reviews(
        self, sponsored_reviews_data: List[List[str]]
    ) -> List[Dict[str, Any]]:
        """Process sponsored reviews data with validation and filtering."""
        logger.info(
            "Processing sponsored reviews data", total_rows=len(sponsored_reviews_data)
        )
        self.statistics["sponsored_reviews"]["total"] = len(sponsored_reviews_data)

        processed_sponsored_reviews = []

        for row in sponsored_reviews_data:
            try:
                # Skip empty rows
                if not row or all(not cell.strip() for cell in row):
                    continue

                # Skip header rows by checking if they look like column headers
                # (containing words like "Период", "GitHub", "Telegram", "Стоимость" etc.)
                if len(row) >= 1 and any(
                    keyword.lower() in str(row[0]).lower()
                    for keyword in [
                        "период",
                        "github",
                        "telegram",
                        "стоимость",
                        "ревью",
                        "месяц",
                    ]
                ):
                    continue

                # Also skip rows where all cells are empty except the first one (period-only rows)
                if (
                    len(row) >= 1
                    and str(row[0]).strip()
                    and all(not str(cell).strip() for cell in row[1:])
                ):
                    continue

                # Actual data structure (A:E):
                # A: Period (Январь, 2025) - this is part of the data, not a header
                # B: GitHub URL of project
                # C: Telegram message URL
                # D: Mentor Telegram username (@pronkin_artem)
                # E: Cost ($20,00)
                # F: Optional additional columns

                if len(row) < 5:
                    logger.warning(
                        "Sponsored review row has insufficient columns", row=row
                    )
                    self.statistics["sponsored_reviews"]["validation_errors"] += 1
                    continue

                # Extract and clean data
                period = (
                    str(row[0]).strip() if row[0] else None
                )  # Period (Январь, 2025)
                project_github_url = (
                    str(row[1]).strip() if row[1] else None
                )  # GitHub URL of project
                telegram_message_url = (
                    str(row[2]).strip() if row[2] else None
                )  # Telegram message URL
                mentor_telegram = (
                    str(row[3]).strip() if row[3] else None
                )  # Mentor telegram username
                cost_str = (
                    str(row[4]).strip() if row[4] else None
                )  # Cost as string ($20,00)

                # Validate required fields (github_url, mentor_telegram, cost are essential)
                if not all([mentor_telegram, project_github_url, cost_str]):
                    logger.warning(
                        "Sponsored review missing required fields",
                        mentor_telegram=mentor_telegram,
                        project_github_url=project_github_url,
                        cost_str=cost_str,
                    )
                    self.statistics["sponsored_reviews"]["validation_errors"] += 1
                    continue

                # Validate GitHub URL format
                project_github_url = cast(str, project_github_url)
                if not project_github_url.startswith("https://github.com/"):
                    logger.warning(
                        "Invalid GitHub URL format",
                        project_github_url=project_github_url,
                    )
                    self.statistics["sponsored_reviews"]["validation_errors"] += 1
                    continue

                # Parse cost - remove currency symbols and convert to float
                try:
                    cost_str = cast(str, cost_str)
                    cost_clean = (
                        cost_str.replace("$", "")
                        .replace("€", "")
                        .replace("₽", "")
                        .replace(",", ".")
                        .strip()
                    )
                    cost = float(cost_clean)
                    if cost < 0:
                        logger.warning("Sponsored review has negative cost", cost=cost)
                        self.statistics["sponsored_reviews"]["validation_errors"] += 1
                        continue
                except ValueError:
                    logger.warning(
                        "Sponsored review has invalid cost format", cost_str=cost_str
                    )
                    self.statistics["sponsored_reviews"]["validation_errors"] += 1
                    continue

                # Extract project name from GitHub URL or use as identifier
                project_name = (
                    project_github_url.split("/")[-1].replace(".git", "")
                    if project_github_url
                    else "unknown_project"
                )

                # Create processed record
                sponsored_review_data = {
                    "period": period,
                    "mentor_identifier": mentor_telegram,
                    "project_github_url": project_github_url,
                    "project_name": project_name,
                    "telegram_message_url": telegram_message_url,
                    "cost": cost,
                    "currency": "USD",  # Default based on $ symbol in data
                    "payment_status": "pending",  # Default status
                    "created_at": datetime.utcnow().isoformat(),
                }

                processed_sponsored_reviews.append(sponsored_review_data)
                self.statistics["sponsored_reviews"]["imported"] += 1

                logger.debug(
                    "Sponsored review processed successfully",
                    project_name=project_name,
                    mentor=mentor_telegram,
                    cost=cost,
                )

            except Exception as e:
                logger.error(
                    "Error processing sponsored review row", row=row, error=str(e)
                )
                self.statistics["sponsored_reviews"]["validation_errors"] += 1
                continue

        logger.info(
            "Sponsored reviews processing completed",
            total_processed=len(processed_sponsored_reviews),
            validation_errors=self.statistics["sponsored_reviews"]["validation_errors"],
            imported=self.statistics["sponsored_reviews"]["imported"],
        )

        return processed_sponsored_reviews
