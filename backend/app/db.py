import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Supabase REST Client Configuration
SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

# Singleton client instance for HTTPS communication
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_supabase() -> Client:
    \"\"\"
    FastAPI dependency that provides the Supabase REST client.
    This replaces the previous SQLAlchemy get_db dependency.
    \"\"\"
    return supabase
