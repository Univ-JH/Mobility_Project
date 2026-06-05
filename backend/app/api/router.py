from fastapi import APIRouter

from app.api.v1 import auth, devices, admin, users, events, policies, emergencies, ws

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(devices.router, prefix="/devices", tags=["Devices"])
api_router.include_router(events.router, prefix="/events", tags=["Events"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(policies.router, prefix="/policies", tags=["Policies"])
api_router.include_router(emergencies.router, prefix="/emergencies", tags=["Emergencies"])
api_router.include_router(ws.router, prefix="/ws", tags=["WebSocket"])
