import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Any

from app.schemas.common import create_success_response
from app.repositories.models import User
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register")
async def register(body: RegisterRequest) -> Any:
    existing = await User.find_one(User.email == body.email)
    if existing:
        raise HTTPException(status_code=409, detail="RESOURCE_DUPLICATED")
    user = User(
        userId=str(uuid.uuid4()),
        email=body.email,
        name=body.name,
        passwordHash=hash_password(body.password),
    )
    await user.insert()
    token = create_access_token(user.userId, role="user")
    return create_success_response(
        data={"accessToken": token, "userId": user.userId, "role": "user"},
        message="회원가입 성공",
    )


@router.post("/login")
async def login(credentials: LoginRequest) -> Any:
    user = await User.find_one(User.email == credentials.email)
    if not user or not user.passwordHash:
        raise HTTPException(status_code=401, detail="AUTH_INVALID_CREDENTIALS")
    if not verify_password(credentials.password, user.passwordHash):
        raise HTTPException(status_code=401, detail="AUTH_INVALID_CREDENTIALS")
    role = "admin" if user.isAdmin else "user"
    token = create_access_token(user.userId, role=role)
    return create_success_response(
        data={"accessToken": token, "role": role},
        message="로그인 성공",
    )
