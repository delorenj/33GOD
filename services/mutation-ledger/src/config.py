from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    exchange_name: str = "bloodbank.events.v1"
    queue_name: str = "services.hookd.mutation_ledger"
    routing_key_pattern: str = "tool.mutation.#"
    consumer_prefetch_count: int = 10

    # Qdrant
    qdrant_url: str = "http://172.19.0.22:6333"
    qdrant_api_key: str = ""
    qdrant_collection_prefix: str = "mutations"

    # Embedding model (fastembed, runs locally)
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = 384

    # SQLite local cache (optional, for fast CLI queries)
    sqlite_cache_enabled: bool = True

    class Config:
        env_file = ".env"
        env_prefix = "MUTATION_LEDGER_"
        # Also read unprefixed vars for shared config
        extra = "ignore"


# Support both prefixed and unprefixed env vars for shared config
class SharedSettings(BaseSettings):
    rabbit_url: str = "amqp://guest:guest@localhost:5672/"
    exchange_name: str = "bloodbank.events.v1"
    qdrant_api_key: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


def load_settings() -> Settings:
    """Load settings with fallback to shared (unprefixed) env vars."""
    shared = SharedSettings()
    s = Settings()

    # Fallback: use shared RABBIT_URL if prefixed one wasn't set
    if s.rabbitmq_url == "amqp://guest:guest@localhost:5672/" and shared.rabbit_url != "amqp://guest:guest@localhost:5672/":
        s.rabbitmq_url = shared.rabbit_url
    if not s.qdrant_api_key and shared.qdrant_api_key:
        s.qdrant_api_key = shared.qdrant_api_key
    if s.exchange_name == "bloodbank.events.v1" and shared.exchange_name != "bloodbank.events.v1":
        s.exchange_name = shared.exchange_name

    return s


settings = load_settings()
