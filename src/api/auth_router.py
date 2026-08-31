"""
Authentication Router: Registration, Login, Token Issuance, and Profile endpoints.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from src.db.database import create_connection
from src.security.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, UserRole, UserSession, TokenResponse,
    RegisterRequest, LoginRequest
)

logger = logging.getLogger("ciris.api.auth")
router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])


@router.get("/banks", response_model=List[Dict[str, Any]])
def list_supported_banks():
    """Returns list of active banks for registration and complaint targeting."""
    conn = create_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, ifsc_prefix, nodal_email FROM auth_banks WHERE is_active = 1 ORDER BY name ASC;")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: RegisterRequest):
    """Registers a new user (Citizen, Bank Official, or Govt Official) and issues a JWT token."""
    # Validation checks based on role
    if payload.role == UserRole.BANK_OFFICIAL and not payload.bank_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bank Officials must be assigned to a valid banking institution (bank_id required)."
        )

    if payload.role == UserRole.GOVT_OFFICIAL and not payload.govt_badge_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Government Officials must provide an official Badge/Nodal ID (govt_badge_id required)."
        )

    conn = create_connection()
    try:
        cursor = conn.cursor()
        
        # Check if email already exists
        cursor.execute("SELECT id FROM auth_users WHERE email = ?;", (payload.email.lower().strip(),))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email address already exists."
            )

        # Validate bank exists if provided
        bank_name = None
        if payload.bank_id:
            cursor.execute("SELECT name FROM auth_banks WHERE id = ?;", (payload.bank_id,))
            b_row = cursor.fetchone()
            if not b_row:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bank_id.")
            bank_name = b_row["name"]

        user_id = f"USR_{payload.role.value}_{uuid.uuid4().hex[:8].upper()}"
        hashed_pwd = hash_password(payload.password)
        now = datetime.now(timezone.utc).isoformat()

        cursor.execute("""
            INSERT INTO auth_users (id, email, hashed_password, full_name, phone_number, role, bank_id, govt_badge_id, is_verified, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?);
        """, (
            user_id,
            payload.email.lower().strip(),
            hashed_pwd,
            payload.full_name.strip(),
            payload.phone_number.strip(),
            payload.role.value,
            payload.bank_id,
            payload.govt_badge_id.strip() if payload.govt_badge_id else None,
            now
        ))
        conn.commit()

        user_data = {
            "id": user_id,
            "email": payload.email.lower().strip(),
            "role": payload.role.value,
            "bank_id": payload.bank_id
        }
        token = create_access_token(user_data)

        user_session = UserSession(
            id=user_id,
            email=payload.email.lower().strip(),
            full_name=payload.full_name.strip(),
            phone_number=payload.phone_number.strip(),
            role=payload.role,
            bank_id=payload.bank_id,
            bank_name=bank_name,
            govt_badge_id=payload.govt_badge_id,
            is_verified=True
        )

        return TokenResponse(access_token=token, user=user_session)
    finally:
        conn.close()


@router.post("/login", response_model=TokenResponse)
def login_user(payload: LoginRequest):
    """Authenticates credentials, verifies role constraints, and returns a signed JWT access token."""
    conn = create_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.email, u.hashed_password, u.full_name, u.phone_number, u.role, u.bank_id, u.govt_badge_id, u.is_verified, b.name AS bank_name
            FROM auth_users u
            LEFT JOIN auth_banks b ON u.bank_id = b.id
            WHERE u.email = ?;
        """, (payload.email.lower().strip(),))
        row = cursor.fetchone()

        if not row or not verify_password(payload.password, row["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )

        if not bool(row["is_verified"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is currently inactive. Contact system administrator."
            )

        user_role = UserRole(row["role"])
        if payload.expected_role and user_role != payload.expected_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: This account belongs to {user_role.value}, not {payload.expected_role.value}."
            )

        user_data = {
            "id": row["id"],
            "email": row["email"],
            "role": row["role"],
            "bank_id": row["bank_id"]
        }
        token = create_access_token(user_data)

        user_session = UserSession(
            id=row["id"],
            email=row["email"],
            full_name=row["full_name"],
            phone_number=row["phone_number"],
            role=user_role,
            bank_id=row["bank_id"],
            bank_name=row["bank_name"],
            govt_badge_id=row["govt_badge_id"],
            is_verified=bool(row["is_verified"])
        )

        return TokenResponse(access_token=token, user=user_session)
    finally:
        conn.close()


@router.get("/me", response_model=UserSession)
def get_my_profile(current_user: UserSession = Depends(get_current_user)):
    """Returns the authenticated session profile."""
    return current_user
