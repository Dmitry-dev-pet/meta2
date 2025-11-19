"""
Main import service that orchestrates the data import process.
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional, cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, text

from ..config.settings import settings
from ..models import (
    User,
    Role,
    MentorProfile,
    Project,
    Review,
    SponsoredReview,
)
from ..services.google_sheets import get_google_sheets_client
from ..services.data_processor import DataProcessor
from ..utils.validation import normalize_github_url_canonical
from structlog import get_logger

logger = get_logger(__name__)


class ImportService:
    """Service for importing data from Google Sheets to the database."""

    def __init__(self):
        """Initialize the import service."""
        self.google_sheets_client = get_google_sheets_client()
        self.data_processor = DataProcessor()

    async def run_full_import(self) -> Dict[str, Any]:
        """
        Run the complete data import process.

        Returns:
            Import result with statistics
        """
        logger.info("Starting full data import")

        try:
            # Step 1: Fetch raw data from Google Sheets
            raw_data = await self.google_sheets_client.fetch_all_data()

            # Save raw data for debugging
            await self.google_sheets_client.save_raw_data(raw_data)

            # Step 2: Process data with Telegram filtering
            processed_result = await self.data_processor.process_all_data(raw_data)

            # Step 3: Import to database
            import_result = await self._import_to_database(
                processed_result["processed_data"]
            )

            # Step 4: Generate final report
            final_report = await self._generate_report(processed_result, import_result)

            # Save report for debugging
            await self._save_report(final_report)

            logger.info("Full data import completed successfully", report=final_report)

            return final_report

        except Exception as e:
            logger.error("Data import failed", error=str(e))
            raise

    async def _import_to_database(
        self, processed_data: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Import processed data to database.

        Args:
            processed_data: Processed data from data processor

        Returns:
            Import statistics
        """
        logger.info("Starting database import")

        import_stats = {
            "students": {"created": 0, "errors": 0},
            "mentors": {"created": 0, "errors": 0},
            "projects": {"created": 0, "linking_errors": 0},
            "reviews": {"created": 0, "linking_errors": 0},
            "sponsored_reviews": {"created": 0, "linking_errors": 0},
        }

        # Get database adapter
        from ..config.database import get_database_adapter

        db_adapter = get_database_adapter()

        async with db_adapter.async_session_factory() as session:
            try:
                # Clear existing data (Full Replace strategy)
                await self._clear_database(session)

                # Create mappings for linking
                github_to_user_id: Dict[str, int] = {}
                telegram_to_user_id: Dict[str, int] = {}

                # Import users (students + mentors)
                await self._import_users(
                    session,
                    processed_data["students"],
                    "STUDENT",
                    github_to_user_id,
                    telegram_to_user_id,
                    import_stats,
                )
                await self._import_users(
                    session,
                    processed_data["mentors"],
                    "MENTOR",
                    github_to_user_id,
                    telegram_to_user_id,
                    import_stats,
                )

                # Import mentor profiles
                await self._import_mentor_profiles(
                    session,
                    processed_data["mentors"],
                    telegram_to_user_id,
                    import_stats,
                )

                # Import projects
                project_name_to_id: Dict[str, int] = {}
                await self._import_projects(
                    session,
                    processed_data["projects"],
                    github_to_user_id,
                    project_name_to_id,
                    import_stats,
                )

                # Import reviews
                await self._import_reviews(
                    session,
                    processed_data["reviews"],
                    project_name_to_id,
                    telegram_to_user_id,
                    import_stats,
                )

                # Import sponsored reviews if enabled
                if (
                    settings.enable_financial_import
                    and "sponsored_reviews" in processed_data
                ):
                    await self._import_sponsored_reviews(
                        session,
                        processed_data["sponsored_reviews"],
                        project_name_to_id,
                        telegram_to_user_id,
                        import_stats,
                    )

                # Commit transaction
                await session.commit()

                logger.info(
                    "Database import completed successfully", statistics=import_stats
                )
                return import_stats

            except Exception as e:
                await session.rollback()
                logger.error(
                    "Database import failed, transaction rolled back", error=str(e)
                )
                raise

    async def _clear_database(self, session: AsyncSession) -> None:
        """Clear existing data in correct order, checking table existence first."""
        logger.info("Clearing existing database data")

        # Check and clear tables in correct order to respect foreign key constraints
        table_models = [
            SponsoredReview,
            Review,
            MentorProfile,
            Project,
            User,  # This will cascade to user_roles
        ]

        for model in table_models:
            try:
                # Check if table exists before clearing
                table_name = model.__tablename__
                check_table_exists = text(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
                )
                result = await session.execute(check_table_exists)
                table_exists = result.fetchone() is not None

                if table_exists:
                    await session.execute(delete(model))
                    logger.info(f"Cleared table: {table_name}")
                else:
                    logger.info(f"Table {table_name} does not exist, skipping")

            except Exception as e:
                logger.warning(
                    f"Error clearing table {getattr(model, '__tablename__', 'unknown')}: {str(e)}"
                )

        # Note: We don't delete roles as they should be static

    async def _import_users(
        self,
        session: AsyncSession,
        users_data: List[Dict[str, Any]],
        role_name: str,
        github_to_user_id: Dict[str, int],
        telegram_to_user_id: Dict[str, int],
        import_stats: Dict[str, Any],
    ) -> None:
        """Import users with their roles."""
        logger.info(f"Importing {role_name.lower()}s", count=len(users_data))

        # Get role
        role = await self._get_or_create_role(session, role_name)

        for user_data in users_data:
            try:
                # Check if user already exists
                existing_user = await self._find_existing_user(session, user_data)

                if existing_user:
                    # Use existing user and update if needed
                    user = existing_user
                    # For mentors, always set telegram_user_id to None (they don't have it in Google Sheets)
                    if role_name == "MENTOR":
                        # Avoid mypy Column[int] vs Optional[int] assignment issues
                        setattr(user, "telegram_user_id", None)
                    else:
                        user.telegram_user_id = (
                            user_data.get("telegram_user_id") or user.telegram_user_id
                        )
                    user.github_url = user_data.get("github_url") or user.github_url
                else:
                    # Create new user
                    user = User(
                        telegram_username=user_data["telegram_username"],
                        telegram_user_id=user_data.get("telegram_user_id"),
                        github_url=user_data.get("github_url"),
                    )
                    session.add(user)
                    await session.flush()  # Get the ID

                # Add role if not already assigned using direct insert to avoid lazy loading
                from ..models.user import user_roles
                from sqlalchemy import select

                stmt = select(user_roles).where(
                    (user_roles.c.user_id == user.id)
                    & (user_roles.c.role_id == role.id)
                )
                result = await session.execute(stmt)
                if not result.scalar_one_or_none():
                    await session.execute(
                        user_roles.insert().values(user_id=user.id, role_id=role.id)
                    )

                # Update mappings
                if user.github_url:
                    github_to_user_id[cast(str, user.github_url)] = cast(int, user.id)
                if user.telegram_username:
                    telegram_to_user_id[cast(str, user.telegram_username).lower()] = (
                        cast(int, user.id)
                    )

                # Update statistics
                key = "students" if role_name == "STUDENT" else "mentors"
                import_stats[key]["created"] += 1

            except Exception as e:
                logger.error("Error importing user", user_data=user_data, error=str(e))
                key = "students" if role_name == "STUDENT" else "mentors"
                import_stats[key]["errors"] += 1

    async def _import_mentor_profiles(
        self,
        session: AsyncSession,
        mentors_data: List[Dict[str, Any]],
        telegram_to_user_id: Dict[str, int],
        import_stats: Dict[str, Any],
    ) -> None:
        """Import mentor profiles."""
        logger.info("Importing mentor profiles", count=len(mentors_data))

        for mentor_data in mentors_data:
            try:
                telegram_username = mentor_data.get("telegram_username")
                if (
                    not telegram_username
                    or telegram_username not in telegram_to_user_id
                ):
                    continue

                user_id = telegram_to_user_id[telegram_username]

                # Check if profile already exists
                existing_profile = await session.get(MentorProfile, user_id)

                if existing_profile:
                    # Update existing profile
                    profile = existing_profile
                else:
                    # Create new profile
                    profile = MentorProfile(user_id=user_id)
                    session.add(profile)

                # Update profile data
                profile_data = mentor_data.get("profile", {})
                profile.full_name = profile_data.get("full_name")
                profile.languages = profile_data.get("languages")
                profile.services = profile_data.get("services")
                profile.price_type = profile_data.get("price_type")
                profile.website_url = profile_data.get("website_url")

            except Exception as e:
                logger.error(
                    "Error importing mentor profile",
                    mentor_data=mentor_data,
                    error=str(e),
                )
                import_stats["mentors"]["errors"] += 1

    async def _import_projects(
        self,
        session: AsyncSession,
        projects_data: List[Dict[str, Any]],
        github_to_user_id: Dict[str, int],
        project_name_to_id: Dict[str, int],
        import_stats: Dict[str, Any],
    ) -> None:
        """Import projects."""
        logger.info("Importing projects", count=len(projects_data))

        for project_data in projects_data:
            try:
                # Find student by GitHub URL
                github_url = project_data.get("author_github_url")
                if not github_url or github_url not in github_to_user_id:
                    import_stats["projects"]["linking_errors"] += 1
                    continue

                student_id = github_to_user_id[github_url]

                # Create project
                project = Project(
                    name=project_data["name"],
                    language=project_data.get("language"),
                    repository_url=project_data.get("repository_url"),
                    submission_date=project_data.get("submission_date"),
                    student_id=student_id,
                )
                session.add(project)
                await session.flush()  # Get the ID

                # Update mapping for review linking
                project_name_to_id[project_data["name"]] = cast(int, project.id)

                import_stats["projects"]["created"] += 1

            except Exception as e:
                logger.error(
                    "Error importing project", project_data=project_data, error=str(e)
                )
                import_stats["projects"]["errors"] = (
                    import_stats["projects"].get("errors", 0) + 1
                )

    async def _import_reviews(
        self,
        session: AsyncSession,
        reviews_data: List[Dict[str, Any]],
        project_name_to_id: Dict[str, int],  # Project name to project ID mapping
        telegram_to_user_id: Dict[str, int],
        import_stats: Dict[str, Any],
    ) -> None:
        """Import reviews using project name for project linking."""
        logger.info("Importing reviews", count=len(reviews_data))
        logger.info(
            "Available project names in mapping",
            project_names=list(project_name_to_id.keys())[:5],
        )
        logger.info(
            "Available mentors in mapping", mentors=list(telegram_to_user_id.keys())[:5]
        )

        for i, review_data in enumerate(reviews_data):
            try:
                # Find mentor and project
                mentor_telegram = review_data.get("mentor_telegram")
                project_name = review_data.get("project_name")
                repository_url = review_data.get("repository_url")  # Keep for debugging

                logger.debug(
                    f"Processing review {i+1}",
                    mentor_telegram=mentor_telegram,
                    project_name=project_name,
                    repository_url=repository_url,
                )

                mentor_id = (
                    telegram_to_user_id.get(mentor_telegram)
                    if isinstance(mentor_telegram, str)
                    else None
                )
                project_id = (
                    project_name_to_id.get(project_name)
                    if isinstance(project_name, str)
                    else None
                )

                logger.debug(
                    "Lookup results", mentor_id=mentor_id, project_id=project_id
                )

                if not mentor_id:
                    import_stats["reviews"]["linking_errors"] += 1
                    logger.warning("Mentor not found", mentor_telegram=mentor_telegram)
                    continue

                if not project_id:
                    import_stats["reviews"]["linking_errors"] += 1
                    logger.warning(
                        "Project not found",
                        project_name=project_name,
                        repository_url=repository_url,
                    )
                    continue

                # Create review for the specific project
                review = Review(
                    project_id=project_id,
                    mentor_id=mentor_id,
                    period_date=review_data.get("period_date"),
                    review_type=review_data.get("review_type"),
                    review_url=review_data.get("review_url"),
                )
                session.add(review)

                import_stats["reviews"]["created"] += 1

            except Exception as e:
                logger.error(
                    "Error importing review", review_data=review_data, error=str(e)
                )
                import_stats["reviews"]["errors"] = (
                    import_stats["reviews"].get("errors", 0) + 1
                )

    async def _find_existing_user(
        self, session: AsyncSession, user_data: Dict[str, Any]
    ) -> Optional[User]:
        """Find existing user by unique identifiers (case-insensitive for telegram_username)."""
        # Try telegram username first (required)
        telegram_username = user_data.get("telegram_username")
        if telegram_username:
            # Case-insensitive search for telegram_username
            stmt = select(User).where(
                func.lower(User.telegram_username) == telegram_username.lower()
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

        # Fallback to GitHub URL
        github_url = user_data.get("github_url")
        if github_url:
            stmt = select(User).where(User.github_url == github_url)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

        return None

    async def _get_or_create_role(self, session: AsyncSession, role_name: str) -> Role:
        """Get existing role or create new one."""
        stmt = select(Role).where(Role.name == role_name)
        result = await session.execute(stmt)
        role = result.scalar_one_or_none()

        if not role:
            role = Role(name=role_name)
            session.add(role)
            await session.flush()

        return role

    async def _generate_report(
        self, processed_result: Dict[str, Any], import_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate final import report."""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "completed",
            "processing_statistics": processed_result["statistics"],
            "import_statistics": import_stats,
            "success": True,
        }

        # Calculate success rates
        for entity in ["students", "mentors"]:
            if processed_result["statistics"][entity]["total"] > 0:
                passed = processed_result["statistics"][entity]["passed_filter"]

                created = import_stats[entity]["created"]
                report[f"{entity}_success_rate"] = (
                    (created / passed) if passed > 0 else 0
                )

        return report

    async def _save_report(self, report: Dict[str, Any]) -> None:
        """Save import report to file."""
        try:
            import os

            # Ensure backup directory exists
            os.makedirs(settings.backup_dir, exist_ok=True)

            # Save to file
            filepath = os.path.join(settings.backup_dir, "import_report.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            logger.info("Import report saved", filepath=filepath)

        except Exception as e:
            logger.error("Error saving import report", error=str(e))

    async def _find_project_by_github_url(
        self, session: AsyncSession, github_url: str, project_name: Optional[str] = None
    ) -> Optional[int]:
        """
        Find project ID by GitHub URL using enhanced matching strategies.

        Args:
            session: Database session
            github_url: GitHub URL to match
            project_name: Optional project name for logging

        Returns:
            Project ID if found, None otherwise
        """
        if not github_url:
            return None

        # Normalize the input GitHub URL to canonical form
        canonical_url = normalize_github_url_canonical(github_url)
        if not canonical_url:
            logger.warning(
                "Invalid GitHub URL format",
                github_url=github_url,
                project_name=project_name,
            )
            return None

        logger.debug(
            "Searching for project",
            github_url=github_url,
            canonical_url=canonical_url,
            project_name=project_name,
        )

        # Strategy 1: Exact canonical URL match
        result = await session.execute(
            select(Project).where(Project.repository_url == canonical_url)
        )
        project = result.scalar_one_or_none()
        if project:
            logger.debug(
                "Found project by exact URL match",
                project_id=project.id,
                project_name=project.name,
                github_url=github_url,
                canonical_url=canonical_url,
            )
            return cast(int, project.id)

        # Strategy 2: Try matching with canonical forms of existing project URLs
        # Get all projects with repository URLs
        result = await session.execute(
            select(Project).where(Project.repository_url.isnot(None))
        )
        all_projects = result.scalars().all()

        for project in all_projects:
            # Normalize each project's repository URL
            url = cast(Optional[str], project.repository_url)
            if url:
                project_canonical = normalize_github_url_canonical(url)
                if project_canonical and project_canonical == canonical_url:
                    logger.debug(
                        "Found project by canonical URL normalization",
                        project_id=project.id,
                        project_name=project.name,
                        original_url=url,
                        canonical_url=project_canonical,
                        search_url=github_url,
                        search_canonical=canonical_url,
                    )
                    return cast(int, project.id)

        # Strategy 3: Extract owner/repo and try pattern matching
        # Extract owner and repo from canonical URL
        if "github.com/" in canonical_url:
            try:
                path = canonical_url.split("github.com/")[-1]
                parts = path.split("/")
                if len(parts) >= 2:
                    owner, repo = parts[0], parts[1]

                    # Search for projects with matching owner/repo in their repository URLs
                    for project in all_projects:
                        if project.repository_url:
                            project_lower = cast(str, project.repository_url).lower()
                            if (
                                owner.lower() in project_lower
                                and repo.lower() in project_lower
                            ):
                                logger.debug(
                                    "Found project by owner/repo pattern match",
                                    project_id=project.id,
                                    project_name=project.name,
                                    project_url=project.repository_url,
                                    search_owner=owner,
                                    search_repo=repo,
                                )
                                return cast(int, project.id)
            except Exception as e:
                logger.debug(
                    "Error extracting owner/repo from URL",
                    error=str(e),
                    url=canonical_url,
                )

        # Strategy 4: Fuzzy name matching (if project name is provided)
        if project_name:
            search_name = project_name.lower().strip()
            repo_name = canonical_url.split("/")[-1].lower()

            for project in all_projects:
                project_name_lower = project.name.lower().strip()

                # Check for various similarity patterns
                if (
                    search_name in project_name_lower
                    or project_name_lower in search_name
                    or repo_name in project_name_lower
                    or project_name_lower in repo_name
                ):

                    # Calculate a simple similarity score
                    similarity: float = 0.0
                    if search_name in project_name_lower:
                        similarity += len(search_name) / len(project_name_lower)
                    if repo_name in project_name_lower:
                        similarity += len(repo_name) / len(project_name_lower)

                    # Accept if similarity is reasonable (> 0.3)
                    if similarity > 0.3:
                        logger.debug(
                            "Found project by fuzzy name match",
                            project_id=project.id,
                            project_name=project.name,
                            search_name=project_name,
                            repo_name=repo_name,
                            similarity=round(similarity, 2),
                        )
                        return cast(int, project.id)

        logger.debug(
            "Project not found by any matching strategy",
            github_url=github_url,
            canonical_url=canonical_url,
            project_name=project_name,
        )
        return None

    async def _import_sponsored_reviews(
        self,
        session: AsyncSession,
        sponsored_reviews_data: List[Dict[str, Any]],
        project_name_to_id: Dict[str, int],
        telegram_to_user_id: Dict[str, int],
        import_stats: Dict[str, Any],
    ) -> None:
        """
        Import sponsored reviews data into the database.

        Args:
            session: Database session
            sponsored_reviews_data: Processed sponsored reviews data
            project_name_to_id: Mapping from project names to IDs
            telegram_to_user_id: Mapping from telegram usernames to user IDs
            import_stats: Import statistics to update
        """
        logger.info(
            "Importing sponsored reviews", total_reviews=len(sponsored_reviews_data)
        )

        # Pre-validate mentor availability
        missing_mentors = set()
        available_mentors = set(telegram_to_user_id.keys())

        # Pre-validate project availability
        available_projects = set(project_name_to_id.keys())

        logger.info(
            "Pre-validation summary",
            available_mentors=len(available_mentors),
            available_projects=len(available_projects),
        )

        for review_data in sponsored_reviews_data:
            try:
                # Extract data from processed review
                mentor_identifier = review_data.get("mentor_identifier", "")
                project_github_url = review_data.get("project_github_url", "")
                project_name = review_data.get("project_name", "")
                cost = review_data.get("cost")
                currency = review_data.get("currency", "USD")
                payment_status = review_data.get("payment_status", "pending")
                telegram_message_url = review_data.get("telegram_message_url", "")

                # Detailed mentor lookup with error categorization (case-insensitive)
                mentor_id = None
                if mentor_identifier.startswith("@"):
                    mentor_username = mentor_identifier[
                        1:
                    ].lower()  # Convert to lowercase for case-insensitive matching
                    mentor_id = telegram_to_user_id.get(mentor_username)
                    if not mentor_id:
                        missing_mentors.add(mentor_username)
                        logger.warning(
                            "Mentor not found for sponsored review - telegram username not in system",
                            mentor_identifier=mentor_identifier,
                            mentor_username=mentor_username,
                            project_name=project_name,
                            github_url=project_github_url,
                            available_mentors_sample=list(available_mentors)[:5],
                        )
                else:
                    logger.warning(
                        "Invalid mentor identifier format for sponsored review",
                        mentor_identifier=mentor_identifier,
                        expected_format="@username",
                        project_name=project_name,
                        github_url=project_github_url,
                    )

                if not mentor_id:
                    import_stats["sponsored_reviews"]["linking_errors"] += 1
                    continue

                # Find project using enhanced GitHub URL matching
                project_id = await self._find_project_by_github_url(
                    session=session,
                    github_url=project_github_url,
                    project_name=project_name,
                )

                if not project_id:
                    logger.info(
                        "Project not found for sponsored review - linking failed",
                        project_name=project_name,
                        github_url=project_github_url,
                        mentor_identifier=mentor_identifier,
                        review_data=review_data,
                    )
                    import_stats["sponsored_reviews"]["linking_errors"] += 1
                    continue

                # Find the corresponding review using URL-based linking (primary method)
                review_id = await self._find_review_by_url(
                    session, telegram_message_url, mentor_id, project_id
                )

                if review_id:
                    logger.info(
                        "Found review for sponsored review using URL matching",
                        review_id=review_id,
                        telegram_url=telegram_message_url,
                    )
                else:
                    logger.info(
                        "No review found for sponsored review URL - falling back to mentor/project matching",
                        telegram_url=telegram_message_url,
                        mentor_id=mentor_id,
                        project_id=project_id,
                    )

                    # Fallback: Look for a review that matches both mentor and project
                    review_query = (
                        select(Review)
                        .where(
                            Review.mentor_id == mentor_id,
                            Review.project_id == project_id,
                        )
                        .order_by(Review.id.desc())
                    )

                    review_result = await session.execute(review_query)
                    review = review_result.scalar_one_or_none()

                    if review:
                        review_id = cast(int, review.id)
                        logger.info(
                            "Found existing review for sponsored review using mentor/project fallback",
                            review_id=review.id,
                            mentor_id=mentor_id,
                            project_id=project_id,
                        )

                # Create sponsored review record with telegram_message_url
                sponsored_review = SponsoredReview(
                    review_id=review_id,
                    project_id=project_id,
                    mentor_id=mentor_id,
                    cost=cost,
                    currency=currency,
                    payment_status=payment_status,
                    notes=f"Period: {review_data.get('period', 'Unknown')}",
                    telegram_message_url=telegram_message_url,
                )

                # Handle payment date if status is paid
                if payment_status == "paid":
                    # Avoid mypy confusion with SQLAlchemy Column typing
                    setattr(sponsored_review, "payment_date", datetime.utcnow())

                session.add(sponsored_review)
                import_stats["sponsored_reviews"]["created"] += 1

            except Exception as e:
                logger.error(
                    "Error importing sponsored review",
                    review_data=review_data,
                    error=str(e),
                )
                continue

        # Enhanced final logging with error analysis
        total_processed = len(sponsored_reviews_data)
        success_count = import_stats["sponsored_reviews"]["created"]
        error_count = import_stats["sponsored_reviews"]["linking_errors"]
        success_rate = (
            (success_count / total_processed * 100) if total_processed > 0 else 0
        )

        logger.info(
            "Sponsored reviews import completed with detailed statistics",
            total_processed=total_processed,
            successfully_created=success_count,
            linking_errors=error_count,
            success_rate=f"{success_rate:.1f}%",
            missing_mentors_count=len(missing_mentors),
            missing_mentors=list(missing_mentors)[:10] if missing_mentors else None,
        )

        # Provide recommendations for fixing linking errors
        if error_count > 0:
            error_rate = error_count / total_processed * 100
            logger.warning(
                "Linking errors detected - recommendations for improvement",
                error_rate=f"{error_rate:.1f}%",
                recommendations=[
                    "Add missing mentors to the users table with telegram usernames",
                    "Verify GitHub URLs in sponsored reviews match projects table",
                    "Check for repository renames or moves in GitHub",
                    "Consider manual data cleanup for persistent mismatches",
                ],
            )

    async def _find_review_by_url(
        self,
        session: AsyncSession,
        telegram_message_url: str,
        mentor_id: int,
        project_id: int,
    ) -> Optional[int]:
        """
        Find review by exact URL matching only.

        Args:
            session: Database session
            telegram_message_url: URL from sponsored reviews data
            mentor_id: Mentor ID (not used in exact matching)
            project_id: Project ID (not used in exact matching)

        Returns:
            Review ID if exact match found, None otherwise
        """
        if not telegram_message_url:
            return None

        logger.debug(
            "Searching for review by exact URL match", url=telegram_message_url
        )

        # Only exact URL match - no fallback strategies
        exact_match_query = select(Review).where(
            Review.review_url == telegram_message_url
        )
        result = await session.execute(exact_match_query)
        review = result.scalar_one_or_none()

        if review:
            logger.debug(
                "Found review by exact URL match",
                review_id=review.id,
                url=telegram_message_url,
            )
            return cast(int, review.id)

        logger.debug("No review found by exact URL match", url=telegram_message_url)
        return None
