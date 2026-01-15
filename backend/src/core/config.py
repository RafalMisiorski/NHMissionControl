"""
NH Mission Control - Configuration
===================================

All application settings loaded from environment variables.
Uses pydantic-settings for validation and type conversion.
"""

from functools import lru_cache
from typing import Literal

from pydantic import RedisDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==========================================================================
    # Application
    # ==========================================================================
    APP_NAME: str = "NH Mission Control"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production", "test"] = "development"
    DEBUG: bool = False

    # ==========================================================================
    # API
    # ==========================================================================
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ==========================================================================
    # Database (supports SQLite and PostgreSQL)
    # ==========================================================================
    DATABASE_URL: str = "sqlite+aiosqlite:///./nhmc.db"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False

    @computed_field  # type: ignore[misc]
    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.DATABASE_URL
    
    # ==========================================================================
    # Redis
    # ==========================================================================
    REDIS_URL: RedisDsn = "redis://localhost:6379/0"  # type: ignore
    
    # ==========================================================================
    # Authentication
    # ==========================================================================
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION-USE-LONG-RANDOM-STRING"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Password requirements
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    
    # ==========================================================================
    # Email (SendGrid)
    # ==========================================================================
    SENDGRID_API_KEY: str | None = None
    EMAIL_FROM: str = "noreply@neuroholding.ai"
    EMAIL_FROM_NAME: str = "NH Mission Control"
    
    # ==========================================================================
    # External Services
    # ==========================================================================
    UPWORK_API_KEY: str | None = None
    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None

    # ==========================================================================
    # SyncWave Integration
    # ==========================================================================
    SYNCWAVE_ENABLED: bool = True  # Enabled - connects to SyncWave
    SYNCWAVE_API_URL: str = "http://localhost:8756"
    SYNCWAVE_API_KEY: str = "syncwave-local"  # Local development key
    
    # ==========================================================================
    # Rate Limiting
    # ==========================================================================
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # ==========================================================================
    # Computed Properties
    # ==========================================================================
    @computed_field  # type: ignore[misc]
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"
    
    @computed_field  # type: ignore[misc]
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    @computed_field  # type: ignore[misc]
    @property
    def is_test(self) -> bool:
        return self.ENVIRONMENT == "test"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience export
settings = get_settings()
