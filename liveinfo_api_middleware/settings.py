from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # YouTube Settings
    ytlive_channel_id: str = ""
    ytlive_api_key: str = ""
    ytlive_dump_path: str = ""
    ytlive_interval: int = 60  # in seconds

    # NicoNico Live Settings
    nicolive_user_id: str = ""
    nicolive_dump_path: str = ""
    nicolive_interval: int = 60  # in seconds

    # API Settings
    cors_allow_origins: str = ""

    # Common Settings
    useragent: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
