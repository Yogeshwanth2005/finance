import os
from dotenv import load_dotenv

load_dotenv()

# Regulatory Gate:
# True: Show named financial products (for private demo/portfolio use)
# False: Omit named products to comply with SEBI/IRDAI licensing for public use
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

# Database Config
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# App Settings
APP_TITLE = "Fin API"
API_VERSION = "v2"
