from pathlib import Path

from environs import Env

BASE_DIR = Path(__file__).parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage"

LOG_DIR = STORAGE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

DATA_DIR = STORAGE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

env = Env(expand_vars=True)
env.read_env()
