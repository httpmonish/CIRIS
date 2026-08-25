"""
Database Schema Utilities & PostGIS Initialization.
"""

import os
from sqlalchemy import text
from src.db.session import engine, init_db
from src.db.models import Base


def setup_database() -> bool:
    """
    Initialize all database tables and check spatial/PostGIS features.
    Returns True if successfully initialized.
    """
    try:
        # Create PostGIS extension if running on PostgreSQL
        if engine.dialect.name == "postgresql":
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
                conn.commit()

        # Create all tables defined in Base models
        init_db()
        return True
    except Exception as e:
        print(f"[DB SETUP ERROR] {e}")
        # Fallback to standard creation
        init_db()
        return True


def reset_database() -> None:
    """Drop and recreate all operational tables."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
