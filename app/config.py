import os
from dotenv import load_dotenv

load_dotenv()

# ---- Gemini / Google Cloud ----
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

# ---- Mock switches (per-service override wins over master switch) ----
USE_MOCKS = os.getenv("USE_MOCKS", "true").lower() == "true"


def mock_for(service: str) -> bool:
    override = os.getenv(f"{service}_MOCK")
    if override is not None:
        return override.lower() == "true"
    return USE_MOCKS


# ---- Databricks ----
_raw_host = os.getenv("DATABRICKS_HOST", "").strip().rstrip("/")
DATABRICKS_HOST = _raw_host if _raw_host.startswith("http") else f"https://{_raw_host}" if _raw_host else ""
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN", "")
DATABRICKS_WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "")
# Fully-qualified table: <catalog>.<schema>.<table> — must match sql/setup.sql
DATABRICKS_TABLE = os.getenv("DATABRICKS_TABLE", "main.default.loop_segments")

# ---- Shopify ----
SHOPIFY_SHOP = os.getenv("SHOPIFY_SHOP", "")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_TOKEN", "")
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-07")
#SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY")
#SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")

# ---- Bloomreach ----
BLOOMREACH_PROJECT_ID = os.getenv("BLOOMREACH_PROJECT_ID", "")
#BLOOMREACH_API_KEY = os.getenv("BLOOMREACH_API_KEY", "")
BLOOMREACH_CAMPAIGN_ID = os.getenv("BLOOMREACH_CAMPAIGN_ID", "")
BLOOMREACH_BASE_URL = os.getenv("BLOOMREACH_BASE_URL", "https://api.exponea.com")
BLOOMREACH_CUSTOMER_ID_TYPE = os.getenv("BLOOMREACH_CUSTOMER_ID_TYPE", "registered")
BLOOMREACH_API_SECRET= os.getenv("BLOOMREACH_API_SECRET", "")
BLOOMREACH_API_KEY_ID = os.getenv("BLOOMREACH_API_KEY_ID", "")

# ---- Loomi Connect MCP (Bloomreach, T6) ----
# Demo server per hackathon docs; regional: us/eu/uk/ca/ap.connect.loomi.ai/mcp
LOOMI_MCP_URL = os.getenv("LOOMI_MCP_URL", "https://brx.connect.loomi.ai/mcp")
MCP_ENABLED = os.getenv("MCP_ENABLED", "false").strip().lower() == "true"
