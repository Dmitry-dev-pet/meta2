"""
User-related SQLAlchemy models.
"""

from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, Table
from sqlalchemy.orm import relationship
from ..config.database import Base

# Many-to-many relationship table between Users and Roles
user_roles = Table(
    "users_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
)


class User(Base):
    """User model for authentication and user management."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_user_id = Column(BigInteger, unique=True, nullable=True, index=True)
    telegram_username = Column(String(255), unique=True, nullable=True, index=True)
    github_url = Column(String(500), unique=True, nullable=True, index=True)

    # Relationships
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    mentor_profile = relationship("MentorProfile", back_populates="user", uselist=False)
    student_projects = relationship("Project", back_populates="student")
    mentor_reviews = relationship("Review", back_populates="mentor")


class Role(Base):
    """Role model for user role management."""

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)

    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")


class MentorProfile(Base):
    """Extended profile information for mentors."""

    __tablename__ = "mentor_profiles"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)

    # Profile information
    full_name = Column(String(255), nullable=True)
    languages = Column(String(1000), nullable=True)  # Comma-separated languages
    services = Column(String(1000), nullable=True)  # Comma-separated services
    price_type = Column(String(50), nullable=True)
    website_url = Column(String(500), nullable=True)

    # Relationships
    user = relationship("User", back_populates="mentor_profile")
