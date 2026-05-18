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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events for FastAPI application.
    Executes startup and shutdown logics.
    """
    # 1. MongoDB Connection Setup (Beanie)
    client = await init_db()
    
    # 2. MQTT Worker Startup
    mqtt_task = asyncio.create_task(start_mqtt_worker())
    
    yield
    
    # 3. Graceful Shutdown
    mqtt_task.cancel()
    client.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
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
