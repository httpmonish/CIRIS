"""
CIRIS API Dependencies.
"""

from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session
from src.db.session import get_db


def get_db_session() -> Generator[Session, None, None]:
    """Provide database session dependency."""
    yield from get_db()
