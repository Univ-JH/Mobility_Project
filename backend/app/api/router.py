from fastapi import APIRouter

from app.api.v1 import auth, devices, admin

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(devices.router, prefix="/devices", tags=["Devices"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
