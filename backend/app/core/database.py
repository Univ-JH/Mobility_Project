from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from beanie import init_beanie
from app.core.config import settings

from app.repositories.models import Device, Event, User, ControlCommandLog, EmergencyCase, Policy

_db: AsyncIOMotorDatabase = None

def get_db() -> AsyncIOMotorDatabase:
    return _db

async def init_db():
    global _db
    # Fix for Beanie 2.1.0 + Motor 3.7+ compatibility
    if not hasattr(AsyncIOMotorClient, "append_metadata"):
        AsyncIOMotorClient.append_metadata = lambda self, *args, **kwargs: None

    client = AsyncIOMotorClient(settings.MONGODB_URL)
    database = client[settings.DATABASE_NAME]
    _db = database

    await init_beanie(
        database=database,
        document_models=[Device, Event, User, ControlCommandLog, EmergencyCase, Policy]
    )

    return client
