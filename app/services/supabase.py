from supabase import create_client, Client
from app.config import settings

supabase: Client | None = None


def get_supabase() -> Client:
    global supabase
    if supabase is None:
        if not settings.supabase_url or not settings.supabase_service_key:
            raise RuntimeError("Supabase not configured — set SUPABASE_URL and SUPABASE_SERVICE_KEY")
        supabase = create_client(settings.supabase_url, settings.supabase_service_key)
    return supabase
