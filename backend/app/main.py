import asyncio
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings

from beanie import init_beanie
from app.api.router import api_router
from app.repositories.models import Device, Event, User
from app.workers.mqtt_client import start_mqtt_worker

from app.core.database import init_db

async def _heartbeat_gc_loop() -> None:
    """Background task: reset stale devices to IDLE every 60 seconds."""
    from app.repositories.device_repo import reset_stale_devices
    while True:
        await asyncio.sleep(60)
        try:
            await reset_stale_devices()
        except Exception as e:
            print(f"[Heartbeat GC] Error: {e}")


async def _seed_admin() -> None:
    from app.repositories.models import User
    from app.core.security import hash_password
    existing = await User.find_one(User.isAdmin == True)
    if existing:
        return
    admin = User(
        userId=str(uuid.uuid4()),
        email=settings.ADMIN_EMAIL,
        name=settings.ADMIN_NAME,
        passwordHash=hash_password(settings.ADMIN_PASSWORD),
        isAdmin=True,
    )
    await admin.insert()
    print(f"[Seed] Admin created: {settings.ADMIN_EMAIL}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. MongoDB Connection Setup (Beanie)
    client = await init_db()

    # 2. Seed default admin if none exists
    await _seed_admin()

    # 3. MQTT Worker Startup
    mqtt_task = asyncio.create_task(start_mqtt_worker())

    # 4. Heartbeat GC — reset stale devices to IDLE
    gc_task = asyncio.create_task(_heartbeat_gc_loop())

    yield

    # 5. Graceful Shutdown
    mqtt_task.cancel()
    gc_task.cancel()
    client.close()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Set all CORS enabled origins (Allowing all for MVP)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (MVP only. In prod, specify the exact domains)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Core Router Inclusion
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/v1/ops/health", tags=["Ops"])
async def health_check():
    """
    Simple health check endpoint.
    """
    return {
        "success": True, 
        "code": "OK",
        "message": "System is healthy",
        "data": {
            "version": "0.1.0",
            "db_status": "mock",
            "mqtt_status": "mock"
        },
        "traceId": str(uuid.uuid4())
    }
