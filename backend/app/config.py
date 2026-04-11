from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8")

    discord_token: str = ""
    discord_guild: str = ""
    alldebrid_api_key: str = ""
    download_path: str = "/data/media"
    wawacity_url: str = "https://www.wawacity.city/"
    darkiworld_url: str = "https://darkiworld16.com"
    darkiworld_email: str = ""
    darkiworld_password: str = ""
    database_url: str = "sqlite+aiosqlite:///./dl_bot.db"
    max_concurrent_downloads: int = 2
    backend_url: str = "http://localhost:8000"


settings = Settings()
