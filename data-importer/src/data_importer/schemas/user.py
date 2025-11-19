"""
Pydantic schemas for user-related data.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from .project import Project, Review


class RoleBase(BaseModel):
    """Base role schema."""

    name: str = Field(..., min_length=1, max_length=50, description="Role name")


class RoleCreate(RoleBase):
    """Schema for creating a role."""

    pass


class Role(RoleBase):
    """Role response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class MentorProfileBase(BaseModel):
    """Base mentor profile schema."""

    full_name: Optional[str] = Field(
        None, max_length=255, description="Mentor full name"
    )
    languages: Optional[str] = Field(
        None, max_length=1000, description="Programming languages"
    )
    services: Optional[str] = Field(
        None, max_length=1000, description="Services offered"
    )
    price_type: Optional[str] = Field(None, max_length=50, description="Pricing model")
    website_url: Optional[str] = Field(
        None, max_length=500, description="Personal website"
    )


class MentorProfileCreate(MentorProfileBase):
    """Schema for creating a mentor profile."""

    pass


class MentorProfile(MentorProfileBase):
    """Mentor profile response schema."""

    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    updated_at: datetime


class UserBase(BaseModel):
    """Base user schema."""

    telegram_username: str = Field(
        ..., min_length=1, max_length=255, description="Telegram username"
    )
    telegram_user_id: Optional[int] = Field(None, description="Telegram user ID")
    github_url: Optional[str] = Field(
        None, max_length=500, description="GitHub profile URL"
    )


class UserCreate(UserBase):
    """Schema for creating a user."""

    roles: Optional[List[str]] = Field(
        default_factory=list, description="List of role names"
    )


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    telegram_username: Optional[str] = Field(None, min_length=1, max_length=255)
    telegram_user_id: Optional[int] = None
    github_url: Optional[str] = Field(None, max_length=500)


class User(UserBase):
    """User response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    roles: List[Role] = Field(default_factory=list, description="User roles")
    mentor_profile: Optional[MentorProfile] = None


class UserWithProjects(User):
    """User schema with related projects."""

    student_projects: List["Project"] = Field(
        default_factory=list, description="Projects as student"
    )
    mentor_reviews: List["Review"] = Field(
        default_factory=list, description="Reviews as mentor"
    )
