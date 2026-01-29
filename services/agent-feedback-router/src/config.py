from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    agentforge_api_url: str = Field(
        "http://localhost:8000", alias="AGENTFORGE_API_URL"
    )
    agentforge_api_token: str | None = Field(None, alias="AGENTFORGE_API_TOKEN")
    request_timeout_seconds: float = Field(30.0, alias="AGENTFORGE_API_TIMEOUT")

    class Config:
        populate_by_name = True


settings = Settings()
