"""Admin authentication dependency.

AUTH_MODE=dev: no real auth, returns dev admin identity.
AUTH_MODE=token: requires Bearer token (returns 501 for now).
"""

from fastapi import Depends, HTTPException, Header

from app.config import settings

DEV_ADMIN = {
    "admin_id": "local-dev-admin",
    "email": "local-dev-admin@survivor.local",
    "roles": ["admin"],
}


def get_current_admin(authorization: str | None = Header(None)) -> dict:
    if settings.auth_mode == "dev":
        return DEV_ADMIN

    # TODO: implement real token validation
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    raise HTTPException(status_code=501, detail="Token auth not implemented yet")
