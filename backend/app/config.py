from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    discord_token: str = ""
    discord_guild: str = ""
    alldebrid_api_key: str = ""
    download_path: str = "/data/media"
    wawacity_url: str = "https://www.wawacity.city/"
    database_url: str = "sqlite+aiosqlite:///./dl_bot.db"
    max_concurrent_downloads: int = 2
    backend_url: str = "http://localhost:8000"


settings = Settings()
