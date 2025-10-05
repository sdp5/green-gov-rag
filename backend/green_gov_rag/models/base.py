"""Database configuration and session management."""

from __future__ import annotations

from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

from green_gov_rag.config import settings

# Get database URL from centralized settings
DATABASE_URL = settings.database_url or "sqlite:///./data/greengovrag.db"

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    pool_pre_ping=True,  # Verify connections before using
)


def init_db() -> None:
    """Initialize database tables."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Get database session.

    Usage:
        with get_session() as session:
            session.add(obj)
            session.commit()
    """
    with Session(engine) as session:
        yield session
