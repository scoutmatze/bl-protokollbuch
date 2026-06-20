"""Zentrale Konfiguration aus Umgebungsvariablen (siehe infra/.env.example)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Datenbank / Queue
    database_url: str = "postgresql+psycopg://protokoll:protokoll@db:5432/protokollbuch"
    redis_url: str = "redis://redis:6379/0"

    # Ollama / Modelle
    ollama_base_url: str = "http://ollama:11434"
    llm_model: str = "llama3.1"
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = 768

    # Auth
    jwt_secret: str = "change-me"
    access_token_ttl_min: int = 60

    # Ingestion / Matching
    protokoll_source_dir: str = "/data/quelle"
    match_t_high: float = 0.82
    match_t_low: float = 0.62

    log_level: str = "INFO"


settings = Settings()
