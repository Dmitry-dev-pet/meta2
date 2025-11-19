"""
Data validation utilities.
"""

import re
from typing import Optional
from datetime import date
from structlog import get_logger

logger = get_logger(__name__)


def normalize_telegram_username(username: str) -> Optional[str]:
    """
    Normalize Telegram username.

    Args:
        username: Raw telegram username

    Returns:
        Normalized username without @ prefix in lowercase, or None if invalid
    """
    if not username:
        return None

    # Remove @ prefix if present and convert to lowercase
    normalized = username.strip().lstrip("@").lower()

    # Check if it's a valid telegram username (letters, numbers, underscores)
    if not re.match(r"^[a-zA-Z0-9_]+$", normalized):
        return None

    return normalized


def normalize_github_url(url: str) -> Optional[str]:
    """
    Normalize GitHub URL.

    Args:
        url: Raw GitHub URL or username

    Returns:
        Normalized GitHub URL, or None if invalid
    """
    if not url:
        return None

    url = url.strip()

    # Handle double prefix issues like "https://github.com/https://gist.github.com/username"
    if "https://github.com/https://" in url:
        # Extract the actual URL part after the double prefix
        parts = url.split("https://github.com/https://")
        if len(parts) > 1:
            # Handle gist URLs
            if "gist.github.com" in parts[1]:
                # Extract username from gist URL
                gist_parts = parts[1].split("gist.github.com/")
                if len(gist_parts) > 1:
                    username = gist_parts[1].split("/")[0]
                    return f"https://github.com/{username}" if username else None
            # Handle other double prefixes
            elif parts[1].startswith("github.com/"):
                return f"https://{parts[1]}"

    # Handle different formats
    if url.startswith("https://github.com/"):
        return url
    elif url.startswith("http://github.com/"):
        return url.replace("http://", "https://")
    elif url.startswith("github.com/"):
        return f"https://{url}"
    elif url.startswith("https://gist.github.com/"):
        # Extract username from gist URL
        gist_parts = url.split("gist.github.com/")
        if len(gist_parts) > 1:
            username = gist_parts[1].split("/")[0]
            return f"https://github.com/{username}" if username else None
    elif "/" in url and not url.startswith("http"):
        # Assume it's a username/repo format
        return f"https://github.com/{url}"
    else:
        # Assume it's a username
        return f"https://github.com/{url}"

    # Fallback: if none of the patterns matched explicitly
    return None


def normalize_github_url_canonical(url: str) -> Optional[str]:
    """
    Normalize GitHub URL to canonical form for matching.

    This function creates a standardized form of GitHub URLs that can be used
    for reliable matching between different data sources.

    Args:
        url: Raw GitHub URL

    Returns:
        Canonical GitHub URL or None if invalid
    """
    if not url:
        return None

    url = str(url).strip()

    # Handle double prefix issues
    if "https://github.com/https://" in url:
        parts = url.split("https://github.com/https://")
        if len(parts) > 1:
            url = parts[1]

    # Extract the core GitHub path (owner/repo)
    if "github.com" in url:
        # Extract path after github.com/
        path = url.split("github.com/")[-1]

        # Remove protocol prefix if it exists in the path
        if path.startswith("https://"):
            path = path[8:]
        elif path.startswith("http://"):
            path = path[7:]

        # Remove www. if present
        if path.startswith("www."):
            path = path[4:]
    else:
        # Assume the URL is already in owner/repo format
        path = url

    # Clean up the path
    # Remove .git suffix
    path = path.rstrip(".git")

    # Remove trailing slash
    path = path.rstrip("/")

    # Remove any URL fragments (#)
    if "#" in path:
        path = path.split("#")[0]

    # Remove any query parameters (?)
    if "?" in path:
        path = path.split("?")[0]

    # Validate that we have a proper owner/repo format
    if not path or "/" not in path:
        return None

    parts = path.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        return None

    # Return canonical form
    return f"https://github.com/{parts[0]}/{parts[1]}"


def extract_github_url_from_repository(repository_url: str) -> Optional[str]:
    """
    Extract GitHub URL from repository URL.

    Args:
        repository_url: Repository URL that may be in different formats

    Returns:
        GitHub URL of the author, or None if invalid
    """
    if not repository_url:
        return None

    # If it's already a GitHub URL, extract the owner part
    if "github.com" in repository_url:
        # Remove https://github.com/ prefix and get the owner
        repo_path = repository_url.split("github.com/")[-1]
        if "/" in repo_path:
            owner = repo_path.split("/")[0]
            return f"https://github.com/{owner}"

    return None


def parse_period(period_str: str) -> Optional[date]:
    """
    Parse Russian period string to a date object.

    Args:
        period_str: Period string like "Ноябрь, 2021"

    Returns:
        datetime.date for the first day of the month, or None if invalid
    """
    if not period_str:
        return None

    month_map = {
        "Январь": 1,
        "Февраль": 2,
        "Март": 3,
        "Апрель": 4,
        "Май": 5,
        "Июнь": 6,
        "Июль": 7,
        "Август": 8,
        "Сентябрь": 9,
        "Октябрь": 10,
        "Ноябрь": 11,
        "Декабрь": 12,
    }

    try:
        parts = period_str.replace(",", "").strip().split()
        if len(parts) >= 2:
            month_name = parts[0]
            year = int(parts[1])
            month = month_map.get(month_name)
            if month:
                return date(year, month, 1)
    except (ValueError, IndexError):
        pass

    return None


def validate_has_review(value: str) -> bool:
    """
    Validate has_review field.

    Args:
        value: String value from spreadsheet

    Returns:
        Boolean indicating if review exists
    """
    if not value:
        return False

    value = str(value).strip().lower()
    return value in ["есть", "да", "true", "yes", "1", "есть ревью"]


def validate_row_length(
    row: list, expected_length: int, row_type: str = "data"
) -> bool:
    """
    Validate that a row has the expected minimum length.

    Args:
        row: Row data
        expected_length: Minimum expected length
        row_type: Type of row for logging

    Returns:
        True if row is valid, False otherwise
    """
    if not row or len(row) < expected_length:
        logger.warning(
            "Invalid row length",
            row_type=row_type,
            actual_length=len(row) if row else 0,
            expected_length=expected_length,
        )
        return False
    return True


def clean_string(value: str) -> str:
    """
    Clean string value.

    Args:
        value: String to clean

    Returns:
        Cleaned string
    """
    if not value:
        return ""

    return str(value).strip()


def clean_and_validate(row: list, field_validators: dict) -> dict:
    """
    Clean and validate a row of data.

    Args:
        row: Raw row data
        field_validators: Dictionary mapping field names to validation functions

    Returns:
        Dictionary of cleaned data
    """
    cleaned_data = {}
    errors = []

    for field_name, (index, validator) in field_validators.items():
        try:
            # Get raw value
            raw_value = row[index] if index < len(row) else None

            # Clean string
            if isinstance(raw_value, str):
                raw_value = clean_string(raw_value)

            # Apply validator
            if validator:
                cleaned_value = validator(raw_value)
                cleaned_data[field_name] = cleaned_value
            else:
                cleaned_data[field_name] = raw_value

        except Exception as e:
            errors.append(f"Error in field {field_name}: {str(e)}")
            cleaned_data[field_name] = None

    if errors:
        logger.warning("Validation errors in row", errors=errors, row=row)

    return cleaned_data
