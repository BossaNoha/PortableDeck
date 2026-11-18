"""Input validation shared by score and pot confirmation actions."""
from .actionerrors import ActionValidationError


def validate_confirmation(approved):
    if not isinstance(approved, bool):
        raise ActionValidationError("invalid_confirmation", "Confirmation must be True or False.")
