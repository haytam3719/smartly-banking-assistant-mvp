from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_name: str = "smartly-ai-banking-assistant"
    log_level: str = "INFO"
    debug: bool = False

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-5.4-mini"
    openai_router_model: str = "gpt-5.4-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    llm_timeout_seconds: float = 20.0

    banking_backend_mode: str = "mock"
    banking_api_base_url: str = "http://localhost:9000"
    banking_api_timeout_seconds: float = 3.0
    banking_api_token: str = "demo-token"

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "banking-knowledge"
    rag_top_k: int = Field(default=5, ge=1, le=20)
    rag_score_threshold: float = Field(default=0.55, ge=0.0, le=1.0)

    database_url: str = "postgresql+asyncpg://banking:banking@localhost:5432/banking_ai"
    langgraph_postgres_uri: str = "postgresql://banking:banking@localhost:5432/banking_ai?sslmode=disable"
    langgraph_checkpoints_enabled: bool = False
    langgraph_aes_key: str = ""
    langgraph_strict_msgpack: bool = True

    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 120

    otel_enabled: bool = False
    otel_service_name: str = "banking-ai-assistant"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"

    max_message_chars: int = 4000
    max_tools_per_request: int = 3
    expose_debug_trace: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
