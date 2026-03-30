"""
Configuration management for the Caching Proxy.
All configuration settings are loaded from the environment variables.
"""

from pydantic import Field
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings - all from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Application Settings
    app_name: str = Field(
        default="CachingProxy", description="The name of the application"
    )
    app_version: str = Field(
        default="0.1.0", description="The version of the application"
    )
    base_url: str = Field(
        default="http://localhost:8000", description="The base URL of the application"
    )
    support_email: str = Field(..., description="The support email of the application")

    # Redis Settings
    redis_host: str = Field(..., description="The host of the Redis database")
    redis_port: int = Field(..., description="The port of the Redis database")
    redis_username: str = Field(..., description="The username of the Redis database")
    redis_password: str = Field(..., description="The password of the Redis database")

    @property
    def redis_url(self) -> str:
        """Generate Redis connection URL."""

        return f"redis://{self.redis_username}:{self.redis_password}@{self.redis_host}:{self.redis_port}"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings instance
    """
    return Settings()


settings = get_settings()
