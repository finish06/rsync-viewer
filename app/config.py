from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Rsync Log Viewer"
    debug: bool = False
    database_url: str
    secret_key: str = "change-me"
    default_api_key: str = "rsv_dev_key"


@lru_cache
def get_settings() -> Settings:
    return Settings()
