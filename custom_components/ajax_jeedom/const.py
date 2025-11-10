"""Constants."""
from logging import Logger, getLogger

# Base component constants
NAME = "Jeedom Ajax Bridge"
DOMAIN = "ajax_jeedom"
DOMAIN_DATA = f"{DOMAIN}_data"
LOGGER: Logger = getLogger(__package__)


# Configuration and options
CONF_BASE_URL = "base_url"
CONF_AUTH_TOKEN = "auth_token"
CONF_PANIC_BUTTON = "panic_button"
CONF_REPLACE_USERNAME = "replace_username"
CONF_APPLY_HUB_STATE_TO_GROUPS = "apply_hub_state_to_groups"
CONF_API_URL = "/plugins/ajaxSystem/core/php/jeeAjaxSystem.php"
