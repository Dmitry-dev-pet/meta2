"""
Project-related SQLAlchemy models.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Text,
    Date,
    DateTime,
    Numeric,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from ..config.database import Base


class Project(Base):
    """Project model for student submissions."""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)

    # Project information
    name = Column(String(255), nullable=False, index=True)
    language = Column(String(100), nullable=True)
    repository_url = Column(String(500), nullable=True)

    # Submission information
    submission_date = Column(Date, nullable=True)  # Period when project was submitted

    # Foreign key to student
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Relationships
    student = relationship("User", back_populates="student_projects")
    reviews = relationship(
        "Review", back_populates="project", cascade="all, delete-orphan"
    )


class Review(Base):
    """Review model for mentor evaluations."""

    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)

    # Review information
    period_date = Column(Date, nullable=True)  # When the review was made
    review_type = Column(String(100), nullable=True)  # "Видео", "Текст"
    review_url = Column(String(500), nullable=True)

    # Foreign keys
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    mentor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Relationships
    project = relationship("Project", back_populates="reviews")
    mentor = relationship("User", back_populates="mentor_reviews")


class SponsoredReview(Base):
    """Sponsored Review model for financial data with telegram_message_url."""

    __tablename__ = "sponsored_reviews"

    id = Column(Integer, primary_key=True, index=True)

    # Links to existing entities
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    mentor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Financial information
    cost = Column(Numeric(10, 2), nullable=True)  # Стоимость услуги
    currency = Column(String(3), default="RUB", nullable=False)  # Валюта
    payment_status = Column(
        String(20), default="pending", nullable=False
    )  # статус оплаты

    # Dates
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    payment_date = Column(DateTime, nullable=True)
    review_date = Column(Date, nullable=True)  # Дата фактического ревью

    # Additional information
    sponsor_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Кто оплатил
    payment_method = Column(String(50), nullable=True)  # Способ оплаты
    notes = Column(Text, nullable=True)  # Дополнительные заметки
    telegram_message_url = Column(
        String(500), nullable=True
    )  # URL сообщения Telegram с ревью

    # Relationships
    review = relationship("Review", backref="sponsored_reviews")
    mentor = relationship("User", foreign_keys=[mentor_id])
    project = relationship("Project", backref="sponsored_reviews")
    sponsor = relationship("User", foreign_keys=[sponsor_id])
