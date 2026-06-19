import os
import sys
import time
import logging
from pymongo import MongoClient
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("database")

def safe_print(text: str):
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback to ASCII representation for emojis if terminal doesn't support UTF-8
        clean_text = text.replace("✅", "[OK]").replace("❌", "[FAIL]").replace("🚀", "[START]")
        try:
            print(clean_text)
        except Exception:
            try:
                print(text.encode('ascii', errors='replace').decode('ascii'))
            except Exception:
                pass

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

def mask_mongo_uri(uri: str) -> str:
    if not uri:
        return "None"
    try:
        if "://" in uri and "@" in uri:
            prefix, rest = uri.split("://", 1)
            credentials, host_info = rest.split("@", 1)
            return f"{prefix}://********@{host_info}"
        return "********"
    except Exception:
        return "********"

# Mask credentials and print loaded MONGO_URI once at import time
masked_uri = mask_mongo_uri(MONGO_URI)
safe_print(f"Loaded MONGO_URI: {masked_uri}")

# Global connection references
_client = None
_db = None
_is_connected = False
_last_attempt_time = 0.0

def init_db(force: bool = False):
    global _client, _db, _is_connected, _last_attempt_time
    now = time.time()
    if not force and _db is not None:
        return _db

    # Rate limit connection attempts to once every 10 seconds if not forced
    if not force and _client is None and (now - _last_attempt_time < 10.0):
        return _db

    _last_attempt_time = now

    if not MONGO_URI:
        logger.error("MONGO_URI environment variable is not set.")
        safe_print("❌ MongoDB Connection Failed")
        _client = None
        _db = None
        _is_connected = False
        return None

    try:
        logger.info("Connecting to MongoDB...")
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        # Perform admin ping to check connection
        client.admin.command("ping")
        _client = client
        db_name = os.getenv("DB_NAME", "keystroke_saas").strip()
        _db = client[db_name]
        _is_connected = True
        logger.info("MongoDB Connected successfully.")
        safe_print("✅ MongoDB Connected")
    except Exception as exc:
        logger.error(f"MongoDB Connection Failed: {exc}")
        safe_print("❌ MongoDB Connection Failed")
        _client = None
        _db = None
        _is_connected = False

    return _db

# Initialize database at startup/import time
init_db(force=True)

def get_database():
    global _db
    if _db is None:
        init_db()
    return _db

def is_database_connected() -> bool:
    global _is_connected, _client
    if _client is None:
        # Try to connect
        init_db()
    if _client is None:
        return False
    try:
        _client.admin.command("ping")
        _is_connected = True
        return True
    except Exception:
        _is_connected = False
        return False
