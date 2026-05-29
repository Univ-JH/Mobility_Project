from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Mobility Safety System API"
    API_V1_STR: str = "/v1"
    
    # Security (Pre-shared token for Prototype)
    PRE_SHARED_TOKEN: str = "proto-secret-token-123"
    SECRET_KEY: str = "super-secret-jwt-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    
    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017" # default for local dev
    DATABASE_NAME: str = "mobility_db"
    
    # MQTT
    MQTT_BROKER_URL: str = "localhost" # default for local dev
    MQTT_PORT: int = 1883
    MQTT_CLIENT_ID: str = "backend-worker-1"
    
    # Business Logic
    EMERGENCY_WAIT_SEC: int = 30
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

settings = Settings()
