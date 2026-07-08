import json
from pathlib import Path
from functools import lru_cache

CONFIG_DIR = Path(__file__).parent.parent / "configs"


@lru_cache
def load_config(business_id: str):
    config_file = CONFIG_DIR / f"{business_id}.json"

    if not config_file.exists():
        raise FileNotFoundError(f"No config found for '{business_id}'")

    with open(config_file, "r") as f:
        return json.load(f)
