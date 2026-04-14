"""项目配置。"""

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置。"""

    app_name: str = "Code Review Agent"
    app_version: str = "0.1.0"
    host: str = "127.0.0.1"
    port: int = 8000
    database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "REVIEW_AGENT_DATABASE_URL",
            "DATABASE_URL",
            "REVIEW_AGENT_POSTGRES_DSN",
        ),
    )

    dashscope_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "REVIEW_AGENT_DASHSCOPE_API_KEY",
            "DASHSCOPE_API_KEY",
        ),
    )
    dashscope_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        validation_alias=AliasChoices(
            "REVIEW_AGENT_DASHSCOPE_BASE_URL",
            "DASHSCOPE_BASE_URL",
        ),
    )
    dashscope_model: str = Field(
        default="qwen-plus",
        validation_alias=AliasChoices(
            "REVIEW_AGENT_DASHSCOPE_MODEL",
            "DASHSCOPE_MODEL",
        ),
    )
    dashscope_timeout_seconds: float = Field(
        default=30.0,
        validation_alias=AliasChoices("REVIEW_AGENT_DASHSCOPE_TIMEOUT_SECONDS"),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="REVIEW_AGENT_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """返回缓存后的配置对象。"""
    return Settings()
