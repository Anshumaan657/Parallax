from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = "local"
    app_name: str = "parallax-api"
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    database_url: str = "postgresql+asyncpg://parallax:parallax@localhost:5432/parallax"
    redis_url: str = "redis://localhost:6379/0"
    worker_heartbeat_key: str = "parallax:worker:heartbeat"
    worker_heartbeat_ttl_seconds: int = Field(default=30, ge=10, le=300)

    github_token: str = ""
    github_default_repo: str = ""
    slack_bot_token: str = ""
    slack_default_channel: str = "#engineering"
    jira_base_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""
    jira_default_project: str = ""
    notion_token: str = ""
    notion_parent_page_id: str = ""

    agent_service_url: str = "http://localhost:8100"
    agent_service_api_key: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

