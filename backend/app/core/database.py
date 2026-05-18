from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings

# 모델 추가 시 여기에 임포트 추가
from app.repositories.models import Device, Event, User

async def init_db():
    """
    MongoDB 연결 및 Beanie 초기화 함수
    """
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    
    # DB 타임아웃 등 추가 설정이 필요한 경우 client.get_io_loop() 등에 접근 가능
    database = client[settings.DATABASE_NAME]
    
    await init_beanie(
        database=database,
        document_models=[Device, Event, User]
    )
    
    return client
