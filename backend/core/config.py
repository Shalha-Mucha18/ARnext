from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Postgres
    PG_HOST: str
    PG_PORT: str = "5432"
    PG_DB: str
    PG_USER: str
    PG_PASSWORD: str
    PG_SCHEMA: str = "public"

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.PG_USER}:{self.PG_PASSWORD}@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DB}"


    # Groq
    GROQ_API_KEY: str
    GROQ_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    LLM_TEMPERATURE: float = 0.0

    # Safety
    DEFAULT_LIMIT: int = 200
    ALLOWED_TABLES: str = "tbldeliveryinfo,AIL_Monthly_Total_Final_Territory,AIL_Monthly_Total_Forecast,AIL_Monthly_Total_Item,dim_business_unit"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    SESSION_TTL_SECONDS: int = 86400

    # API
    DEBUG_RETURN_SQL: bool = Field(default=False)

    class Config:
        # Use absolute path to ensure .env is found regardless of CWD
        import os
        from pathlib import Path
        
        # Calculate path: config.py -> core -> backend -> Steel_AI -> .env
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        env_file = str(env_path) if env_path.exists() else "../.env"
        extra = "ignore"

settings = Settings()
print(f"\\n[CONFIG] Loaded GROQ_MODEL: {settings.GROQ_MODEL}\\n")
