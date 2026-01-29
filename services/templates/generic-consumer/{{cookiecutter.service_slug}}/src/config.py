from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    exchange_name: str = "bloodbank.events"

    class Config:
        env_file = ".env"

settings = Settings()
