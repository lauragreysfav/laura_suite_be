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

    whisparr_url: str = "http://whisparr:6969"
    whisparr_api_key: str = ""

    prowlarr_url: str = "http://prowlarr:9696"
    prowlarr_api_key: str = ""

    database_path: str = "/data/laura.db"
    log_level: str = "INFO"
    secret_key: str = "change-me"

    model_config = {"env_file": str(Path(__file__).parent.parent / ".env")}


settings = Settings()
