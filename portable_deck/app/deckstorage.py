"""Validate and atomically persist deck definitions without editor widgets."""
import copy
import json
import os

from ..core.deck import Deck


def prepare_deck_definition(types, cards):
    data = copy.deepcopy({"types": types, "cards": cards})
    Deck.validate_data(data)
    return data


def save_deck_definition(path, data, *, overwrite=False):
    """Save validated data; callers obtain overwrite consent before opting in."""
    data = copy.deepcopy(data)
    Deck.validate_data(data)
    path = os.fspath(path)
    if os.path.exists(path) and overwrite is not True:
        raise FileExistsError(f"A deck named '{os.path.basename(path)}' already exists.")
    temporary_path = path + ".tmp"
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(temporary_path, "w", encoding="utf-8") as deck_file:
            json.dump(data, deck_file, indent=2, ensure_ascii=False)
            deck_file.write("\n")
        os.replace(temporary_path, path)
    except OSError:
        if os.path.exists(temporary_path):
            try:
                os.remove(temporary_path)
            except OSError:
                pass
        raise
    return path
