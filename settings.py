"""Load and save the application's user settings."""
import json
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "configs")
CONFIG_PATH = os.path.join(CONFIG_DIR, "settings.json")
DEFAULT_CONFIG_PATH = os.path.join(CONFIG_DIR, "default_settings.json")
DEFAULT_SETTINGS = {
    "num_players": 3,
    "cards_per_player": 5,
    "deck_path": os.path.join("decks", "demodeck.json"),
    "save_discard_on_exit": True,
    "use_custom_player_names": False,
    "player_names": [],
    "enable_score_counter": False,
    "require_point_confirmation": False,
    "allow_take_from_table": False,
    "allow_move_table_card_to_discard": False,
    "allow_manual_table_cleanup": False,
    "clear_table_on_round_end": False,
}


def load_default_settings():
    defaults = DEFAULT_SETTINGS.copy()
    try:
        with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as defaults_file:
            saved_defaults = json.load(defaults_file)
        if isinstance(saved_defaults, dict):
            defaults.update({key: saved_defaults[key] for key in DEFAULT_SETTINGS if key in saved_defaults})
    except (OSError, json.JSONDecodeError):
        pass
    return defaults


def load_settings():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    settings = load_default_settings()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as config_file:
            saved = json.load(config_file)
        if isinstance(saved, dict):
            settings.update({key: saved[key] for key in DEFAULT_SETTINGS if key in saved})
    except (OSError, json.JSONDecodeError):
        pass

    # Create a usable config on first launch and repair missing config files.
    save_settings(settings)
    return settings


def save_settings(settings):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as config_file:
        json.dump(settings, config_file, indent=2)
        config_file.write("\n")


def resolve_deck_path(path):
    if os.path.isabs(path):
        return path
    return os.path.join(BASE_DIR, path)
