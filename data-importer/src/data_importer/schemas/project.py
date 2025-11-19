"""
Pydantic schemas for project-related data.
"""

from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, HttpUrl
from .user import User


class ProjectBase(BaseModel):
    """Base project schema."""

    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    language: Optional[str] = Field(
        None, max_length=100, description="Programming language"
    )
    repository_name: Optional[str] = Field(
        None, max_length=255, description="Repository name"
    )
    repository_url: Optional[HttpUrl] = Field(None, description="Repository URL")
    submission_date: Optional[date] = Field(None, description="Project submission date")
    has_review: bool = Field(False, description="Whether project has a review")


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""

    student_id: int = Field(..., description="Student user ID")


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    language: Optional[str] = Field(None, max_length=100)
    repository_name: Optional[str] = Field(None, max_length=255)
    repository_url: Optional[HttpUrl] = None
    submission_date: Optional[date] = None
    has_review: Optional[bool] = None


class Project(ProjectBase):
    """Project response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    created_at: datetime
    updated_at: datetime


class ProjectWithDetails(Project):
    """Project schema with related user and reviews."""

    student: "User" = Field(..., description="Student information")
    reviews: List["Review"] = Field(default_factory=list, description="Project reviews")


class ReviewBase(BaseModel):
    """Base review schema."""

    period_date: Optional[date] = Field(None, description="Review period date")
    review_type: Optional[str] = Field(
        None, max_length=100, description="Review type (Video, Text)"
    )
    review_url: Optional[HttpUrl] = Field(None, description="Review URL")


class ReviewCreate(ReviewBase):
    """Schema for creating a review."""

    project_id: int = Field(..., description="Project ID")
    mentor_id: int = Field(..., description="Mentor user ID")


class ReviewUpdate(BaseModel):
    """Schema for updating a review."""

    period_date: Optional[date] = None
    review_type: Optional[str] = Field(None, max_length=100)
    review_url: Optional[HttpUrl] = None


class Review(ReviewBase):
    """Review response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    mentor_id: int
    created_at: datetime
    updated_at: datetime


class ReviewWithDetails(Review):
    """Review schema with related project and mentor."""

    project: "Project" = Field(..., description="Project information")
    mentor: "User" = Field(..., description="Mentor information")
