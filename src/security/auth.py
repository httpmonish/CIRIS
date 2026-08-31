"""
Security, Password Hashing, JWT Token Generation & RBAC Role Guards.
"""

import os
import uuid
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, EmailStr
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.db.database import create_connection

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CIRIS_SUPER_SECRET_KEY_PROD_SIH_2026_RBAC")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

security_bearer = HTTPBearer(auto_error=False)


class UserRole(str, Enum):
    CITIZEN = "CITIZEN"
    BANK_OFFICIAL = "BANK_OFFICIAL"
    GOVT_OFFICIAL = "GOVT_OFFICIAL"


class UserSession(BaseModel):
    id: str
    email: str
    full_name: str
    phone_number: str
    role: UserRole
    bank_id: Optional[str] = None
    bank_name: Optional[str] = None
    govt_badge_id: Optional[str] = None
    is_verified: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSession


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone_number: str
    role: UserRole
    bank_id: Optional[str] = None
    govt_badge_id: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    expected_role: Optional[UserRole] = None


def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = plain_password.encode('utf-8')[:72]
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


def create_access_token(user_data: Dict[str, Any]) -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": user_data["id"],
        "email": user_data["email"],
        "role": user_data["role"],
        "bank_id": user_data.get("bank_id"),
        "exp": expires
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please authenticate again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)
) -> UserSession:
    """Dependency to extract and validate the authenticated user from the Bearer token."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided. Access denied.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token claims.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user from database
    conn = create_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.email, u.full_name, u.phone_number, u.role, u.bank_id, u.govt_badge_id, u.is_verified, b.name AS bank_name
            FROM auth_users u
            LEFT JOIN auth_banks b ON u.bank_id = b.id
            WHERE u.id = ?;
        """, (user_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account not found or deactivated.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return UserSession(
            id=row["id"],
            email=row["email"],
            full_name=row["full_name"],
            phone_number=row["phone_number"],
            role=UserRole(row["role"]),
            bank_id=row["bank_id"],
            bank_name=row["bank_name"],
            govt_badge_id=row["govt_badge_id"],
            is_verified=bool(row["is_verified"])
        )
    finally:
        conn.close()


class RequireRole:
    """Dependency factory enforcing Role-Based Access Control on endpoints."""
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: UserSession = Depends(get_current_user)) -> UserSession:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of {[r.value for r in self.allowed_roles]}. Your role is {current_user.role.value}."
            )
        return current_user
