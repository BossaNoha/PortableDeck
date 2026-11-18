"""Validated deck import/export without dialogs or widget dependencies."""
import os
import shutil

from ..core.deck import Deck


class InvalidDeckError(ValueError):
    pass


class SameDeckFileError(ValueError):
    pass


def validate_deck_source(source):
    try:
        Deck(source)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise InvalidDeckError(str(error)) from error


def _different_files(source, target):
    if (os.path.normcase(os.path.abspath(source)) == os.path.normcase(os.path.abspath(target))
            or (os.path.exists(target) and os.path.samefile(source, target))):
        raise SameDeckFileError("Source and destination refer to the same deck file.")


def import_deck_target(source, directory):
    """Validate source and resolve a library destination before overwrite consent."""
    validate_deck_source(source)
    filename = os.path.basename(source)
    if not filename.lower().endswith(".json"):
        filename += ".json"
    target = os.path.join(directory, filename)
    _different_files(source, target)
    return target


def _copy_deck(source, target, overwrite):
    _different_files(source, target)
    if os.path.exists(target) and overwrite is not True:
        raise FileExistsError(f"A deck named '{os.path.basename(target)}' already exists.")
    shutil.copy2(source, target)
    return target


def import_deck(source, directory, *, overwrite=False):
    target = import_deck_target(source, directory)
    return _copy_deck(source, target, overwrite)


def export_deck(source, target, *, overwrite=False):
    validate_deck_source(source)
    target = os.fspath(target)
    if not target.lower().endswith(".json"):
        target += ".json"
    return _copy_deck(source, target, overwrite)
