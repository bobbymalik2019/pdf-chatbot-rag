from pydantic_settings import BaseSettings, SettingsConfigDict

from pathlib import Path
from pydantic import Field

class AppSettings(BaseSettings):
    
    rag_api_base_url: str = "http://127.0.0.1:8000"
    
    # PostgreSQL — Chat History database
    db_host: str = "127.0.0.1"
    db_port: int = 5433
    db_name: str = "chat_history_db"
    db_user: str = "chat_history_user"
    db_password: str =Field(min_length=1)

    # Charter26 SSO
    oidc_issuer: str = "https://ssotest.charter26.com"
    oidc_audience: str = "pdf-ingestion-service"
    oidc_client_id: str = "chatbot-gateway"
    oidc_ca_cert_file: Path | None = None

    # Redis connection
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_username: str = "default"
    redis_password: str = Field(min_length=1)

    # Shared JWKS caching and refresh coordination
    jwks_cache_key: str = "charter26:oidc:jwks"
    jwks_cache_ttl_seconds: int = 300
    jwks_refresh_lock_seconds: int = 10
    jwks_forced_refresh_cooldown_seconds: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = AppSettings()
