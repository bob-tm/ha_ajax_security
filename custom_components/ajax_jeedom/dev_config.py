"""Local development settings, separate from config entries."""

import json
from pathlib import Path

from .const import LOGGER

DEV_CONFIG_FILE = "ajax_jeedom_dev.json"


def cache_api_requests_enabled(filename: str) -> bool:
    """Read the local cache switch; missing or invalid settings disable it."""
    try:
        data = json.loads(Path(filename).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return False
    except OSError, ValueError:
        LOGGER.warning(
            "Cannot read %s; development API cache is disabled", DEV_CONFIG_FILE
        )
        return False
    return isinstance(data, dict) and data.get("cache_api_requests") is True
