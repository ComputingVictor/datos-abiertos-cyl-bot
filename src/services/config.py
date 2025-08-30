"""Configuration management."""

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Telegram Bot
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    telegram_webhook_url: Optional[str] = Field(None, env="TELEGRAM_WEBHOOK_URL")
    telegram_webhook_path: str = Field("/webhook", env="TELEGRAM_WEBHOOK_PATH")
    
    # FastAPI
    fastapi_host: str = Field("0.0.0.0", env="FASTAPI_HOST")
    fastapi_port: int = Field(int(os.getenv("PORT", "8000")), env="FASTAPI_PORT")
    fastapi_debug: bool = Field(False, env="FASTAPI_DEBUG")
    
    # Database
    database_url: str = Field("sqlite:///jcyl_bot.db", env="DATABASE_URL")
    
    # JCYL API
    jcyl_api_base_url: str = Field("https://analisis.datosabiertos.jcyl.es", env="JCYL_API_BASE_URL")
    
    # Alerts
    alerts_enabled: bool = Field(True, env="ALERTS_ENABLED")
    alerts_check_interval_hours: int = Field(2, env="ALERTS_CHECK_INTERVAL_HOURS")
    
    # Pagination
    datasets_per_page: int = Field(10, env="DATASETS_PER_PAGE")
    themes_per_page: int = Field(10, env="THEMES_PER_PAGE")
    keywords_per_page: int = Field(10, env="KEYWORDS_PER_PAGE")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    return Settings()