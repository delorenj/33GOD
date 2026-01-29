"""
Configuration for {{ cookiecutter.service_name }}.

Loads settings from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings for {{ cookiecutter.service_name }}."""

    service_name: str = "{{ cookiecutter.service_name }}"
    environment: str = "dev"

    # RabbitMQ settings (inherited from bloodbank defaults)
    rabbit_url: str = "amqp://guest:guest@rabbitmq:5672/"
    exchange_name: str = "bloodbank.events.v1"

    # Service-specific settings
    {% for setting in cookiecutter.service_settings %}
    {{ setting.name }}: {{ setting.type }} = {{ setting.default }}
    {% endfor %}

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
