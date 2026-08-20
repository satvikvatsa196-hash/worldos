from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, RedisDsn
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "WORLDOS"
    
    # Postgres
    POSTGRES_USER: str = "worldos_user"
    POSTGRES_PASSWORD: str = "worldos_password"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "worldos_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    # LLM Configuration
    LLM_PROVIDER: str = "mock"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    @property
    def sync_database_url(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def async_database_url(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore")

settings = Settings()
