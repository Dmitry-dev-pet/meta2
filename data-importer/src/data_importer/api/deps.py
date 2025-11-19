"""
FastAPI dependencies.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator

from ..config.database import get_db_session
from structlog import get_logger

logger = get_logger(__name__)


async def get_current_admin_user():
    """
    Dependency to check if the current user has admin role.

    TODO: Implement actual authentication when Gateway integration is ready.
    For now, this is a placeholder that allows all requests.
    """
    # This is a placeholder - in production, you would validate JWT tokens
    # and check for ADMIN role from Gateway headers
    return True


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.

    Returns:
        Async database session
    """
    async for session in get_db_session():
        yield session


class AdminRequired:
    """
    Custom dependency class for admin access control.
    """

    def __init__(self):
        self.dependency = Depends(get_current_admin_user)

    def __call__(self, admin_user: bool = Depends(get_current_admin_user)):
        if not admin_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        return admin_user


# Create admin dependency instance
admin_required = AdminRequired()
