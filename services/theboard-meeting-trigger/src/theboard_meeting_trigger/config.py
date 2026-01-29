"""Configuration for theboard-meeting-trigger service."""

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service settings."""

    # Bloodbank connection
    bloodbank_rabbitmq_url: str = Field(
        default="amqp://theboard:theboard_rabbit_pass@localhost:5672/",
        description="RabbitMQ connection URL for Bloodbank",
    )

    rabbit_url: str = Field(
        default="amqp://theboard:theboard_rabbit_pass@localhost:5672/",
        description="RabbitMQ connection URL (Bloodbank expects this name)",
    )

    # TheBoard database connection
    theboard_database_url: PostgresDsn = Field(
        default="postgresql+psycopg://theboard:theboard_dev_pass@localhost:5432/theboard",
        description="TheBoard PostgreSQL connection URL",
    )

    # Service configuration
    service_id: str = Field(
        default="theboard-meeting-trigger",
        description="Service identifier for event routing",
    )

    queue_name: str = Field(
        default="theboard_meeting_trigger_queue",
        description="RabbitMQ queue name",
    )

    # Meeting defaults
    default_strategy: str = Field(
        default="sequential",
        description="Default meeting execution strategy",
    )

    default_max_rounds: int = Field(
        default=5,
        description="Default maximum rounds for meetings",
    )

    default_agent_count: int = Field(
        default=5,
        description="Default number of agents to select",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    class Config:
        """Pydantic config."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
