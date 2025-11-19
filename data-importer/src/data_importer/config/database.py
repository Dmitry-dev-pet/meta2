"""
Database adapter that works with both SQLite and PostgreSQL.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

from .settings import settings


class Base(DeclarativeBase):
    """Base SQLAlchemy model."""

    pass


class DatabaseAdapter:
    """Database adapter that works with both SQLite and PostgreSQL."""

    def __init__(self, database_url: str):
        self.database_url = database_url

        # SQLite specific configuration
        connect_args = {}
        if "sqlite" in database_url:
            connect_args = {"check_same_thread": False}

        self.engine = create_async_engine(
            database_url,
            echo=settings.debug,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            connect_args=connect_args if "sqlite" in database_url else {},
        )

        self.async_session_factory = async_sessionmaker(
            bind=self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session."""
        async with self.async_session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    async def create_tables(self):
        """Create all tables (useful for development with SQLite)."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self):
        """Drop all tables (useful for testing)."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite."""
        return "sqlite" in self.database_url

    @property
    def is_postgresql(self) -> bool:
        """Check if using PostgreSQL."""
        return "postgresql" in self.database_url

    async def close(self):
        """Close database connections."""
        await self.engine.dispose()


# Global database adapter instance
_database_adapter: DatabaseAdapter | None = None


def get_database_adapter() -> DatabaseAdapter:
    """Get or create database adapter."""
    global _database_adapter
    if _database_adapter is None:
        _database_adapter = DatabaseAdapter(settings.database_url)
    return _database_adapter


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session."""
    adapter = get_database_adapter()
    async for session in adapter.get_session():
        yield session
