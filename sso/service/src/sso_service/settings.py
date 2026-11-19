from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str
    issuer: str = 'http://127.0.0.1:3100'
    public_origin: str = 'http://127.0.0.1:3100'
    signing_private_key_file: str = 'keys/private.pem'
    signing_public_key_file: str = 'keys/public.pem'
    signing_key_id: str = 'sso-local-key-1'
    secure_cookies: bool = False  # MUST set true for HTTPS deployments
    access_token_seconds: int = Field(default=600, ge=60, le=3600)
    refresh_token_days: int = Field(default=7, ge=1, le=30)
    session_hours: int = Field(default=8, ge=1, le=24)

    @model_validator(mode='after')
    def check_production(self):
        if self.public_origin.startswith('https://') and not self.secure_cookies:
            raise ValueError('SECURE_COOKIES=true required for HTTPS')
        if self.issuer.rstrip('/') != self.public_origin.rstrip('/'):
            raise ValueError('ISSUER and PUBLIC_ORIGIN must match for this single-origin deployment')
        return self


@lru_cache

def get_settings():
    return Settings()
