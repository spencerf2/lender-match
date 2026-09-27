"""Settings. Every environment variable and API key is read here."""

from functools import cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        extra="ignore",
        # Keep secrets out of validation error messages.
        hide_input_in_errors=True,
    )

    database_url: str
    openrouter_api_key: str | None = None


@cache
def get_config() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
