import logging

from config.env import DATA_DIR, env

TG_BOT_TOKEN: str = env.str("TG_BOT_TOKEN", default="")
TG_BOT_NAME: str = env.str("TG_BOT_NAME", default="CTBFashion")
TG_BOT_USERNAME: str = env.str("TG_BOT_USERNAME", default="CTBFashionBot")
TG_BOT_LINK: str = env.str("TG_BOT_LINK", default="https://t.me/CTBFashionBot")
TG_BOT_OWNER_ID = env.int("TG_BOT_OWNER_ID", default=0)

ADMIN_IDS: list[int] = env.list("ADMIN_IDS", default=[], subcast=int)
USER_IDS: list[int] = env.list("USER_IDS", default=[], subcast=int)

DATABASE_URL: str = env.str("DATABASE_URL", default=f"sqlite:///{DATA_DIR / 'database.db'}")
DATABASE_ALLOWED_TABLES: list[str] = env.list("DATABASE_ALLOWED_TABLES", default=[], subcast=str)
DATABASE_RESTRICTED_TABLES: list[str] = env.list(
    "DATABASE_RESTRICTED_TABLES", default=[""], subcast=str
)
DATABASE_EXCLUDED_COLUMNS: list[str] = env.list(
    "DATABASE_EXCLUDED_COLUMNS", default=[""], subcast=str
)

AUDIT_DB_PATH = DATA_DIR / "audit.db"
LLM_MAX_RETRIES: int = env.int("LLM_MAX_RETRIES", default=3)
RESPONSE_MAX_WORDS: int = env.int("RESPONSE_MAX_WORDS", default=30)
SMALLTALK_ENABLED: bool = env.bool("SMALLTALK_ENABLED", default=True)
PROFANITY_FILTER_ENABLED: bool = env.bool("PROFANITY_FILTER_ENABLED", default=True)
CURRENCY_SYMBOL: str = env.str("CURRENCY_SYMBOL", default="$")

OPENROUTER_API_KEY: str = env.str("OPENROUTER_API_KEY", default="")
OPENROUTER_MODEL: str = env.str("OPENROUTER_MODEL", default="")

LOG_LEVEL: str = env.str("LOG_LEVEL", default="INFO")
DEBUG: bool = env.bool("DEBUG", default=False)
if DEBUG:
    LOG_LEVEL = "DEBUG"

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=LOG_LEVEL)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

LOGGER = logging.getLogger(__name__)
