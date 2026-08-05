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
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_key: str = Field(default="", alias="SUPABASE_KEY")
    supabase_service_role_key: str = Field(default="", alias="SUPABASE_SERVICE_ROLE_KEY")
    database_url: str = Field(default="", alias="DATABASE_URL")
    supabase_db_url: str = Field(default="", alias="SUPABASE_DB_URL")

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    @property
    def resolved_supabase_key(self) -> str:
        return self.supabase_key or self.supabase_service_role_key

    @property
    def resolved_database_url(self) -> str:
        return self.database_url or self.supabase_db_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
