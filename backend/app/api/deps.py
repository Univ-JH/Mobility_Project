import jwt
from fastapi import HTTPException, Header
from app.core.config import settings
from app.core.security import decode_access_token


def _extract_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="AUTH_MISSING_TOKEN")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="AUTH_INVALID_SCHEME")
    return token


async def get_current_user(authorization: str = Header(None)) -> str:
    token = _extract_token(authorization)
    try:
        payload = decode_access_token(token)
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="AUTH_INVALID_CREDENTIALS")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="AUTH_TOKEN_EXPIRED")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="AUTH_INVALID_CREDENTIALS")


async def get_current_admin(authorization: str = Header(None)) -> str:
    token = _extract_token(authorization)
    try:
        payload = decode_access_token(token)
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="AUTH_FORBIDDEN")
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="AUTH_INVALID_CREDENTIALS")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="AUTH_TOKEN_EXPIRED")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="AUTH_INVALID_CREDENTIALS")


async def get_device_auth(authorization: str = Header(None)) -> str:
    token = _extract_token(authorization)
    if token != settings.PRE_SHARED_TOKEN:
        raise HTTPException(status_code=403, detail="AUTH_FORBIDDEN")
    return token
