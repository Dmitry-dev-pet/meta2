"""
Application settings with environment variable support using Pydantic v2.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Application
    app_name: str = "Data Importer Service"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

    # Database
    database_url: str
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30

    # Google Sheets
    main_spreadsheet_id: str
    mentors_spreadsheet_id: str
    google_sheets_credentials_path: str
    google_service_account_email: str | None = None

    students_range: str = "Telegram аккаунты студентов!A2:C"
    projects_range: str = "Projects!A2:J"
    reviews_range: str = "Reviews!A2:I"
    mentors_range: str = (
        "Менторы!A5:H29"  # Updated range to include full_name (A) and telegram_username (B)
    )
    sponsored_reviews_range: str = "Спонсируемые ревью!A2:G"  # Financial data range

    # API
    api_v1_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = ["http://localhost:3000"]

    # Authentication
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    auth_service_url: str

    # Import Configuration
    backup_dir: str = "./backups"
    max_backup_files: int = 10
    import_batch_size: int = 100
    import_timeout: int = 3600
    enable_file_debug: bool = True
    enable_financial_import: bool = True  # Enable sponsored reviews import

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: str = "./logs/data_importer.log"

    # Monitoring
    health_check_interval: int = 30
    metrics_enabled: bool = True

    # Timeouts
    google_api_timeout: int = 30
    auth_service_timeout: int = 10

    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite."""
        return "sqlite" in self.database_url

    @property
    def is_postgresql(self) -> bool:
        """Check if using PostgreSQL."""
        return "postgresql" in self.database_url


# Create global settings instance
settings = Settings()
