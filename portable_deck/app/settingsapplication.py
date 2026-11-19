"""Prepare and apply form settings without widgets or game startup."""
import copy

from ..core.settingsvalidation import validate_settings
from .settings import save_settings


class SettingsWriteError(OSError):
    """Distinguish settings-file failure from validation/deck loading failure."""


def prepare_settings(values, current_settings):
    settings = validate_settings(values)
    settings["configuration_name"] = copy.deepcopy(current_settings.get("configuration_name", "Default"))
    settings["configuration_baseline"] = copy.deepcopy(current_settings.get("configuration_baseline", {}))
    return settings


def apply_settings(values, current_settings):
    """Return independent validated settings only after successful persistence."""
    settings = prepare_settings(values, current_settings)
    try:
        save_settings(settings)
    except OSError as error:
        raise SettingsWriteError(str(error)) from error
    return settings
