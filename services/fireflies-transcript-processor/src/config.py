import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    exchange_name: str = "bloodbank.events.v1"
    vault_path: str = os.path.expanduser("~/code/DeLoDocs")

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
