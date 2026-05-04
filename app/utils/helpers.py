from typing import Dict, Any
from datetime import datetime
from app.config.settings import DEFAULT_TIMEZONE

def deep_merge(source: Dict[str, Any], destination: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two dictionaries recursively.
    """
    for key, value in source.items():
        if isinstance(value, dict):
            # if the value is dict, go deeper (recursive)
            node = destination.setdefault(key, {})
            deep_merge(value, node)
        else:
            # if the value is not a dict (str, int, list), overwrite it
            destination[key] = value
    return destination

def get_current_time():
    """
    Get the current time in the default timezone.
    """
    return datetime.now(DEFAULT_TIMEZONE)