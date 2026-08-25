"""
Database Session Manager for CIRIS Prototype Backend.

Supports PostgreSQL + PostGIS (via DATABASE_URL or POSTGRES_URI env var)
with SQLite fallback for local testing and standalone prototyping.
"""

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.db.models import Base

# Read database URL from environment variable or fallback to local SQLite database file
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    os.getenv("POSTGRES_URI", "sqlite:///./ciris_prototype.db")
)

# SQLite multi-threading fix
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency provider yielding SQLAlchemy DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
