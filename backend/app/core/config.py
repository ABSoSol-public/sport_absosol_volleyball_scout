from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Zentrale Konfiguration, überschreibbar per Env-Vars (siehe .env.example im Repo-Root)."""

    model_config = SettingsConfigDict(env_prefix="VOLLEYSCOUT_", env_file=".env", extra="ignore")

    database_url: str = "mysql+pymysql://scout:scout@localhost:3306/volleyscout?charset=utf8mb4"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]
    api_prefix: str = "/api"
    # Login/Session (Muster wie JWT_SECRET/COOKIE_SECURE im yugioh_database-Projekt)
    secret_key: str = "dev-insecure-change-me"  # Produktion: per Env setzen (openssl rand -hex 32)
    cookie_secure: bool = False  # True hinter HTTPS (Reverse Proxy auf der NAS)
    session_ttl_hours: int = 24 * 7


@lru_cache
def get_settings() -> Settings:
    return Settings()
