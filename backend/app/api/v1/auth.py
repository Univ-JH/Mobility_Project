from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
from app.schemas.common import create_success_response

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
async def login(credentials: LoginRequest) -> Any:
    """Mock login for MVP."""
    if credentials.password == "admin":
        return create_success_response(
            data={"accessToken": "mock-jwt-token", "role": "admin"},
            message="로그인 성공"
        )
    raise HTTPException(status_code=401, detail="AUTH_INVALID_CREDENTIALS")
