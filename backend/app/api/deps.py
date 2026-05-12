from fastapi import Depends, HTTPException, Header
from app.core.config import settings

async def get_current_admin(authorization: str = Header(None)) -> str:
    """
    Verify admin token. For MVP/prototyping, we use a mock JWT validation.
    In production, this should decode a real JWT and verify the role.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="AUTH_MISSING_TOKEN")
        
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="AUTH_INVALID_SCHEME")
        
    # Mock validation (from auth.py mock)
    if token != "mock-jwt-token":
        raise HTTPException(status_code=401, detail="AUTH_INVALID_CREDENTIALS")
        
    # Assume the token signifies an admin role for now.
    # In real impl: decode JWT, check payload["role"] == "admin"
    return "admin_user_id"
