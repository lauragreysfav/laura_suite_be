from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_jwt_secret: str = ""

    torbox_api_key: str
    torbox_webdav_user: str = ""
    torbox_webdav_pass: str = ""
    torbox_webdav_url: str = "https://webdav.torbox.app"

    stash_url: str = "http://localhost:9999"
    stash_api_key: str = ""
    stashdb_api_key: str = ""

    whisparr_url: str = "http://whisparr:6969"
    whisparr_api_key: str = ""

    prowlarr_url: str = "http://gluetun:9696"
    prowlarr_api_key: str = ""

    opensearch_hosts: str = "http://opensearch:9200"
    typesense_host: str = "http://typesense:8108"
    typesense_api_key: str = ""
    typesense_timeout: int = 5
    stashdb_rate_limit_seconds: float = 1.0

    database_path: str = "/data/laura.db"
    log_level: str = "INFO"
    secret_key: str = "change-me"

    db_host: str = "postgres"
    db_port: int = 5432
    db_name: str = "laura"
    db_user: str = "laura"
    db_password: str = ""

    proton_vpn_user: str = ""
    proton_vpn_password: str = ""

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    gluetun_token: str = ""

    model_config = {
        "env_file": str(Path(__file__).parent.parent / ".env"),
        "extra": "ignore"
    }


settings = Settings()
