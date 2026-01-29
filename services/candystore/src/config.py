"""Configuration settings for Event Store Manager."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # PostgreSQL configuration
    database_url: str = Field(
        ...,
        description="PostgreSQL connection URL",
        examples=["postgresql://event_store:password@localhost:5432/event_store"],
    )
    database_pool_size: int = Field(
        default=20,
        description="Database connection pool size",
    )
    database_max_overflow: int = Field(
        default=40,
        description="Maximum overflow connections",
    )

    # RabbitMQ configuration
    rabbitmq_url: str = Field(
        ...,
        description="RabbitMQ connection URL",
        examples=["amqp://bloodbank:password@localhost:5672"],
    )
    bloodbank_exchange: str = Field(
        default="bloodbank.events.v1",
        description="Bloodbank exchange name",
    )
    bloodbank_exchange_type: str = Field(
        default="topic",
        description="Exchange type",
    )

    # Service configuration
    event_store_manager_queue: str = Field(
        default="event_store_manager_queue",
        description="RabbitMQ queue name",
    )
    event_store_manager_dlq: str = Field(
        default="event_store_manager_dlq",
        description="Dead letter queue name",
    )
    event_store_manager_host: str = Field(
        default="0.0.0.0",
        description="API server host",
    )
    event_store_manager_port: int = Field(
        default=8080,
        description="API server port",
    )

    # API configuration
    api_prefix: str = Field(
        default="/api/v1",
        description="API route prefix",
    )
    api_cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:3360"],
        description="CORS allowed origins",
    )
    api_default_page_size: int = Field(
        default=100,
        description="Default pagination page size",
    )
    api_max_page_size: int = Field(
        default=1000,
        description="Maximum pagination page size",
    )
    api_max_causation_depth: int = Field(
        default=100,
        description="Maximum depth for causation chain queries",
    )

    # WebSocket configuration
    ws_heartbeat_interval_seconds: int = Field(
        default=30,
        description="WebSocket heartbeat interval",
    )
    ws_max_connections: int = Field(
        default=100,
        description="Maximum WebSocket connections",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )
    log_format: str = Field(
        default="json",
        description="Log format: json or console",
    )

    # Environment
    environment: str = Field(
        default="development",
        description="Environment name",
    )
    enable_debug_logging: bool = Field(
        default=False,
        description="Enable debug logging",
    )
    enable_profiling: bool = Field(
        default=False,
        description="Enable profiling",
    )
    enable_metrics: bool = Field(
        default=True,
        description="Enable metrics collection",
    )


# Global settings instance
settings = Settings()
