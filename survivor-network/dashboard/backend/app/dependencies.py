"""
Shared Dependencies - Local Survivor Network
Handles local JWT authentication and admin verification for Kind cluster.
"""

import os
import jwt
from fastapi import Header, HTTPException, Depends
from datetime import datetime, timezone

from .database import is_admin

# =============================================================================
# Local Auth Configuration
# =============================================================================

# Define this in your K8s Secret or .env
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "survivor-super-secret-key")
ALGORITHM = "HS256"

# =============================================================================
# Admin Authentication
# =============================================================================

async def verify_admin(authorization: str = Header(...)) -> str:
    """
    Verify local JWT token and check if user is an admin in Postgres.
    
    Returns:
        The admin's email address
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, 
            detail="Invalid or missing authorization header"
        )

    token = authorization[7:]  # Remove "Bearer " prefix

    try:
        # Decode local JWT instead of calling Firebase APIs
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub") # 'sub' usually stores the email/id

        if not email:
            raise HTTPException(status_code=401, detail="Token missing subject claim")

        # Verify against your local 'admins' table in Postgres
        if not await is_admin(email):
            raise HTTPException(
                status_code=403,
                detail=f"Access Denied: {email} is not a registered admin"
            )

        return email

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Auth error: {str(e)}")

# =============================================================================
# Optional: Identity Provider Mock (For Dev)
# =============================================================================

def create_access_token(data: dict):
    """Utility to generate a token for local testing without Firebase."""
    to_encode = data.copy()
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)