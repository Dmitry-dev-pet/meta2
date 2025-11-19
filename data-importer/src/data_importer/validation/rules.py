"""Validation rules for data processing."""

from typing import Dict, Tuple, Callable, Any

from ..utils.validation import (
    normalize_telegram_username,
    normalize_github_url,
    parse_period,
)


class ValidationRules:
    """Centralized validation rules for all entity types."""

    @staticmethod
    def student_fields() -> Dict[str, Tuple[int, Callable[[Any], Any]]]:
        """Field validators for student data.

        Returns:
            Dictionary mapping field names to (column_index, validator_function)
        """
        return {
            "github_url": (0, normalize_github_url),
            "telegram_user_id": (
                1,
                lambda x: int(x) if x and str(x).isdigit() else None,
            ),
            "telegram_username": (2, normalize_telegram_username),
        }

    @staticmethod
    def mentor_fields() -> Dict[str, Tuple[int, Callable[[Any], Any]]]:
        """Field validators for mentor data.

        Returns:
            Dictionary mapping field names to (column_index, validator_function)
        """
        return {
            "github_url": (0, normalize_github_url),
            "full_name": (2, lambda x: x.strip() if x else ""),
            "telegram_username": (3, normalize_telegram_username),
            "languages": (4, lambda x: x.strip() if x else ""),
            "services": (5, lambda x: x.strip() if x else ""),
            "price_type": (6, lambda x: x.strip() if x else ""),
            "website_url": (7, lambda x: x.strip() if x else ""),
        }

    @staticmethod
    def project_fields() -> Dict[str, Tuple[int, Callable[[Any], Any]]]:
        """Field validators for project data.

        Returns:
            Dictionary mapping field names to (column_index, validator_function)
        """
        return {
            "name": (1, lambda x: x.strip() if x else None),
            "language": (2, lambda x: x.strip() if x else ""),
            "repository_url": (4, lambda x: x.strip() if x else ""),
            "author_github_url": (6, normalize_github_url),
        }

    @staticmethod
    def review_fields() -> Dict[str, Tuple[int, Callable[[Any], Any]]]:
        """Field validators for review data.

        Returns:
            Dictionary mapping field names to (column_index, validator_function)
        """
        return {
            "project_name": (1, lambda x: x.strip() if x else None),
            "mentor_telegram": (7, normalize_telegram_username),
            "period_date": (0, parse_period),
            "review_type": (4, lambda x: x.strip() if x else ""),
            "review_url": (5, lambda x: x.strip() if x else ""),
            "repository_url": (3, lambda x: x.strip() if x else ""),
        }

    @staticmethod
    def sponsored_review_fields() -> Dict[str, Tuple[int, Callable[[Any], Any]]]:
        """Field validators for sponsored review data.

        Returns:
            Dictionary mapping field names to (column_index, validator_function)
        """
        return {
            "period": (0, lambda x: str(x).strip() if x else None),
            "project_github_url": (1, lambda x: str(x).strip() if x else None),
            "telegram_message_url": (2, lambda x: str(x).strip() if x else None),
            "mentor_telegram": (3, lambda x: str(x).strip() if x else None),
            "cost_str": (4, lambda x: str(x).strip() if x else None),
        }
