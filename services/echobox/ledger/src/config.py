from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    LOG_LEVEL: str = "INFO"
    DB_POOL_MIN: int = 2
    DB_POOL_MAX: int = 10

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
