"""Load and save the application's user settings."""
import json
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_DIR = os.path.join(BASE_DIR, "configs")
CONFIG_PATH = os.path.join(CONFIG_DIR, "settings.json")
DEFAULT_CONFIG_PATH = os.path.join(CONFIG_DIR, "default_settings.json")
APP_DATA_DIR = os.path.join(BASE_DIR, "portable_deck", "data")
DISCARD_PATH = os.path.join(APP_DATA_DIR, "discard.json")
DEFAULT_SETTINGS = {
    "enable_target_score": False, "target_score": 100,
    "enable_score_warning": False, "score_warning": 80,
    "allow_reduce_score": False,
    "configuration_name": "Default",
    "configuration_baseline": {},
    "enable_cards_visibility": False,
    "cards_visibility": [],
    "enable_interactions": False,
    "interaction_options": {},
    "share_team_chips": False,
    "share_team_score": False,
    "enable_team_score": False,
    "enable_roles_teams": False,
    "enable_dealer": False,
    "enable_teams": False,
    "team_count": 1,
    "team_names": [],
    "player_teams": [],
    "dealer_players": [],
    "unequal_personal_piles": False,
    "personal_pile_counts": [],
    "enable_personal_piles": False,
    "personal_pile_count": 1,
    "personal_pile_settings": [],
    "enable_table": True,
    "enable_discard_pile": True,
    "autosave_enabled": True,
    "autosave_count": 5,
    "require_exit_confirmation": True,
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
    "allow_positioned_play": False,
    "allow_move_cards_on_table": False,
    "allow_play_in_front_of_players": False,
    "allow_draw_from_discard": False,
    "draw_from_discard_mode": "top",
    "allow_face_down_table_cards": False,
    "allow_move_table_sequences": False,
    "allow_recycle_discard_to_deck": False,
    "shared_discard_pile_count": 1,
    "personal_discard_pile_count": 0,
    "enable_chip_accounts": False,
    "minimum_bet": 1,
    "starting_balance": 100,
    "require_pot_withdrawal_confirmation": False,
    "occupied_slot_action": "invalid",
    "enable_undo": False,
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
            if "enable_personal_piles" not in saved and saved.get("personal_discard_pile_count", 0) > 0:
                settings["enable_personal_piles"] = True
                settings["personal_pile_count"] = saved["personal_discard_pile_count"]
                settings["personal_discard_pile_count"] = 0
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
