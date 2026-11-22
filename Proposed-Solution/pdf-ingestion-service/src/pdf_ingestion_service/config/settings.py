from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict



class Settings(BaseSettings):
    database_url: str

    ollama_base_url: str = "http://localhost:11434"
    ollama_embedding_model: str = "nomic-embed-text"
    embedding_dimensions: int = 768
    pdf_storage_backend: str = "local"
    pdf_storage_path: Path = Path("storage/documents")

    ollama_llm_model: str = "llama3.1:latest"

    # Charter26 SSO access-token validation
    oidc_issuer: str = "https://ssotest.charter26.com"
    oidc_audience: str = "pdf-ingestion-service"
    oidc_client_id: str = "chatbot-gateway"
    oidc_ca_cert_file: Path | None = None

    # Shared Redis connection
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_username: str = "default"
    redis_password: str

    # Shared JWKS cache
    jwks_cache_key: str = "charter26:oidc:jwks"
    jwks_cache_ttl_seconds: int = 300
    jwks_refresh_lock_seconds: int = 10

    jwks_forced_refresh_cooldown_seconds: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
settings = Settings()
