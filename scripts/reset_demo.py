"""
Reset Demo Script for CIRIS Productization.

Drops and recreates database tables to clear all prototype state.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db.schema import reset_database


def reset_demo():
    print("Resetting CIRIS Prototype Database...")
    reset_database()
    print("Database tables dropped and recreated cleanly.")


if __name__ == "__main__":
    reset_demo()
