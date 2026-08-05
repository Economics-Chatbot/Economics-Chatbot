from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


def normalize_supabase_url(url: str) -> str:
    normalized_url = url.rstrip("/")
    if normalized_url.endswith("/rest/v1"):
        normalized_url = normalized_url[: -len("/rest/v1")]
    return normalized_url


@lru_cache
def get_supabase_client() -> Client:
    settings = get_settings()

    if not settings.supabase_url:
        raise RuntimeError("SUPABASE_URL is required")
    if not settings.resolved_supabase_key:
        raise RuntimeError("SUPABASE_KEY or SUPABASE_SERVICE_ROLE_KEY is required")

    return create_client(
        normalize_supabase_url(settings.supabase_url),
        settings.resolved_supabase_key,
    )
