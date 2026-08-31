"""
CIRIS Authentication & RBAC Database Management.
Defines schemas and persistence for Users, Banks, Complaints, and Actions with Row-Level Security.
"""

import sqlite3
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pathlib import Path
from src.db.database import get_db_path, create_connection

logger = logging.getLogger("ciris.auth.db")


def init_auth_tables(conn: Optional[sqlite3.Connection] = None) -> None:
    """Creates the tables for Users, Banks, Citizen Complaints, and Audit Actions."""
    should_close = False
    if conn is None:
        conn = create_connection()
        should_close = True

    try:
        cursor = conn.cursor()

        # 1. Banks Master Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_banks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                ifsc_prefix TEXT NOT NULL UNIQUE,
                nodal_email TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            );
        """)

        # 2. Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                hashed_password TEXT NOT NULL,
                full_name TEXT NOT NULL,
                phone_number TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('CITIZEN', 'BANK_OFFICIAL', 'GOVT_OFFICIAL')),
                bank_id TEXT REFERENCES auth_banks(id),
                govt_badge_id TEXT,
                is_verified INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            );
        """)

        # 3. Citizen Complaints Table with Row-Level Security foreign keys
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS citizen_complaints (
                id TEXT PRIMARY KEY,
                complaint_number TEXT NOT NULL UNIQUE,
                citizen_id TEXT NOT NULL REFERENCES auth_users(id),
                target_bank_id TEXT NOT NULL REFERENCES auth_banks(id),
                disputed_amount REAL NOT NULL CHECK(disputed_amount > 0),
                transaction_rrn TEXT NOT NULL,
                fraud_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'UNDER_REVIEW', 'ACCOUNT_FROZEN', 'ESCALATED_LEA', 'RESOLVED', 'REJECTED')),
                victim_city TEXT NOT NULL,
                evidence_notes TEXT,
                incident_timestamp TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)

        # 4. Complaint Actions (Audit Trail)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS complaint_actions (
                id TEXT PRIMARY KEY,
                complaint_id TEXT NOT NULL REFERENCES citizen_complaints(id),
                actor_id TEXT NOT NULL REFERENCES auth_users(id),
                actor_role TEXT NOT NULL,
                action_type TEXT NOT NULL,
                notes TEXT,
                timestamp TEXT NOT NULL
            );
        """)

        # 5. LEA Escalation Registry
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lea_escalations (
                id TEXT PRIMARY KEY,
                complaint_id TEXT NOT NULL REFERENCES citizen_complaints(id),
                bank_official_id TEXT NOT NULL REFERENCES auth_users(id),
                lea_jurisdiction TEXT NOT NULL,
                escalation_reason TEXT NOT NULL,
                escalated_at TEXT NOT NULL
            );
        """)

        conn.commit()
        logger.info("Authentication & RBAC tables verified.")
    finally:
        if should_close:
            conn.close()


def seed_default_auth_data(conn: Optional[sqlite3.Connection] = None, hash_func=None) -> None:
    """Seeds master banks, pre-configured demo user accounts, and initial complaints."""
    should_close = False
    if conn is None:
        conn = create_connection()
        should_close = True

    try:
        init_auth_tables(conn)
        cursor = conn.cursor()

        now = datetime.now(timezone.utc).isoformat()

        # Seed Banks
        banks = [
            ("BANK_SBI", "State Bank of India", "SBIN", "nodal.sbi@bank.in", now),
            ("BANK_ICICI", "ICICI Bank", "ICIC", "nodal.icici@bank.in", now),
            ("BANK_HDFC", "HDFC Bank", "HDFC", "nodal.hdfc@bank.in", now),
            ("BANK_AXIS", "Axis Bank", "UTIB", "nodal.axis@bank.in", now),
            ("BANK_PNB", "Punjab National Bank", "PUNB", "nodal.pnb@bank.in", now)
        ]

        for b_id, b_name, b_ifsc, b_email, b_date in banks:
            cursor.execute("""
                INSERT OR IGNORE INTO auth_banks (id, name, ifsc_prefix, nodal_email, is_active, created_at)
                VALUES (?, ?, ?, ?, 1, ?);
            """, (b_id, b_name, b_ifsc, b_email, b_date))

        # Default Demo Users
        # Password for all demo accounts if hash_func provided or standard fallback
        if hash_func:
            citizen_pw = hash_func("Citizen@123")
            bank_icici_pw = hash_func("Bank@123")
            bank_sbi_pw = hash_func("Bank@123")
            govt_pw = hash_func("GovtAdmin@123")
        else:
            citizen_pw = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
            bank_icici_pw = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
            bank_sbi_pw = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
            govt_pw = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"

        demo_users = [
            ("USR_CITIZEN_001", "citizen@ciris.gov.in", citizen_pw, "Rajesh Kumar (Citizen)", "+91 9876543210", "CITIZEN", None, None, 1, now),
            ("USR_BANK_ICICI_001", "nodal.icici@bank.in", bank_icici_pw, "Priya Sharma (Nodal Officer)", "+91 9811223344", "BANK_OFFICIAL", "BANK_ICICI", None, 1, now),
            ("USR_BANK_SBI_001", "nodal.sbi@bank.in", bank_sbi_pw, "Amitabh Roy (Nodal Officer)", "+91 9822334455", "BANK_OFFICIAL", "BANK_SBI", None, 1, now),
            ("USR_GOVT_I4C_001", "officer.i4c@mha.gov.in", govt_pw, "V. K. Saxena (Deputy Director, I4C)", "+91 9900112233", "GOVT_OFFICIAL", None, "I4C-DIRECTOR-0891", 1, now)
        ]

        for u in demo_users:
            cursor.execute("""
                INSERT OR IGNORE INTO auth_users (id, email, hashed_password, full_name, phone_number, role, bank_id, govt_badge_id, is_verified, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, u)

        # Seed Initial Sample Complaints
        complaints = [
            ("CMP_001", "NCRP-2026-9041", "USR_CITIZEN_001", "BANK_ICICI", 14500.00, "UPI409281920192", "UPI_IMPS", "UNDER_REVIEW", "Mumbai", "Sent via fake electricity bill APK link", now, now),
            ("CMP_002", "NCRP-2026-9042", "USR_CITIZEN_001", "BANK_SBI", 45000.00, "SBI881920192831", "INVESTMENT_SCAM", "OPEN", "Hyderabad", "Telegram investment group scam splintered into mule", now, now),
            ("CMP_003", "NCRP-2026-9043", "USR_CITIZEN_001", "BANK_ICICI", 8200.50, "ICIC991029381029", "QR_CODE_SCAM", "ACCOUNT_FROZEN", "Bangalore", "OLX marketplace QR scam", now, now)
        ]

        for c in complaints:
            cursor.execute("""
                INSERT OR IGNORE INTO citizen_complaints (id, complaint_number, citizen_id, target_bank_id, disputed_amount, transaction_rrn, fraud_type, status, victim_city, evidence_notes, incident_timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, c)

        conn.commit()
        logger.info("Default demonstration accounts & sample complaints seeded successfully.")
    finally:
        if should_close:
            conn.close()
