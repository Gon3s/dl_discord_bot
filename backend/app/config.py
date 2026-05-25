from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8")

    discord_token: str = ""
    discord_guild: str = ""
    debrid_provider: str = "alldebrid"
    alldebrid_api_key: str = ""
    realdebrid_api_token: str = ""
    download_path: str = "/data/media"
    wawacity_url: str = "https://www.wawacity.city/"
    database_url: str = "sqlite+aiosqlite:///./dl_bot.db"
    max_concurrent_downloads: int = 2
    magnet_poll_timeout_s: int = 120
    magnet_poll_interval_s: float = 5.0
    selenium_binary_location: str = ""
    backend_url: str = "http://localhost:8000"
    discord_channel_id: str = ""
    bot_notify_url: str = ""
    app_public_url: str = ""
    notification_enabled: bool = True
    notification_interval_hours: int = 6


settings = Settings()
