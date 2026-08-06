from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        alias="OPENAI_EMBEDDING_MODEL",
    )
    openai_chat_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_CHAT_MODEL")
    model_name: str = Field(default="", alias="MODEL_NAME")
    timeout: float = Field(default=30.0, alias="TIMEOUT")
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(default="", alias="SUPABASE_SERVICE_ROLE_KEY")
    database_url: str = Field(default="", alias="DATABASE_URL")
    supabase_db_url: str = Field(default="", alias="SUPABASE_DB_URL")

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    @property
    def resolved_database_url(self) -> str:
        return self.database_url or self.supabase_db_url

    @property
    def resolved_chat_model(self) -> str:
        return self.model_name or self.openai_chat_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
