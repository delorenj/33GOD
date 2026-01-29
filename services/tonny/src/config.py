"""Configuration management for Tonny Agent."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # RabbitMQ Configuration
    rabbitmq_url: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        description="RabbitMQ connection URL",
    )
    bloodbank_exchange: str = Field(
        default="bloodbank.events.v1",
        description="Bloodbank exchange name",
    )
    tonny_queue: str = Field(
        default="services.tonny.agent",
        description="Tonny consumer queue name",
    )
    tonny_dlq: str = Field(
        default="services.tonny.agent.dlq",
        description="Tonny dead letter queue name",
    )

    # Letta Configuration
    letta_base_url: str = Field(
        default="http://localhost:8283",
        description="Letta server base URL",
    )
    letta_api_key: str = Field(
        default="",
        description="Letta API key (if using Letta Cloud)",
    )

    # LLM Provider Configuration
    llm_provider: str = Field(
        default="openai",
        description="LLM provider (openai, anthropic)",
    )
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key",
    )
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API key",
    )
    llm_model: str = Field(
        default="gpt-4.1",
        description="LLM model to use",
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model for Letta",
    )

    # ElevenLabs TTS Configuration
    elevenlabs_api_key: str = Field(
        default="",
        description="ElevenLabs API key",
    )
    elevenlabs_voice_id: str = Field(
        default="21m00Tcm4TlvDq8ikWAM",
        description="ElevenLabs voice ID",
    )
    elevenlabs_model_id: str = Field(
        default="eleven_monolingual_v1",
        description="ElevenLabs TTS model",
    )

    # Service Configuration
    service_host: str = Field(
        default="0.0.0.0",
        description="Service host address",
    )
    service_port: int = Field(
        default=8000,
        description="Service port",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )

    # Performance Configuration
    max_processing_latency_ms: int = Field(
        default=2000,
        description="Maximum acceptable processing latency in milliseconds",
    )
    consumer_prefetch_count: int = Field(
        default=5,
        description="RabbitMQ consumer prefetch count",
    )


# Global settings instance
settings = Settings()
