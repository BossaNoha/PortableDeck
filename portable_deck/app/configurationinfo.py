"""Remember a configuration's source and compare against its original values."""
import copy
from .settings import DEFAULT_SETTINGS, load_default_settings

APP_SETTINGS = {"show_game_log", "color_game_settings_categories", "autosave_enabled", "autosave_count", "require_exit_confirmation", "enable_undo", "num_players"}
METADATA = {"configuration_name", "configuration_baseline"}

def preset_values(settings):
    return {key: copy.deepcopy(value) for key, value in settings.items() if key not in APP_SETTINGS | METADATA}

def configuration_values(settings):
    values = {key: copy.deepcopy(settings.get(key, default)) for key, default in DEFAULT_SETTINGS.items()
              if key not in {"configuration_name", "configuration_baseline"}}
    players = values["num_players"]
    values["player_teams"] = values["player_teams"] or [None] * players
    values["dealer_players"] = values["dealer_players"] or [False] * players
    values["interaction_options"] = {key: value for key, value in values["interaction_options"].items() if value}
    values["personal_pile_counts"] = values["personal_pile_counts"] or [values["personal_pile_count"]] * players
    rules = values["personal_pile_settings"]
    values["personal_pile_settings"] = [[{
        "access": "owner", "ordered": False, "order_by": "time", "new_card": "top", "size_order": "up",
        **(rules[owner][pile] if owner < len(rules) and pile < len(rules[owner]) else {})}
        for pile in range(values["personal_pile_counts"][owner] if values["unequal_personal_piles"] else values["personal_pile_count"])] for owner in range(players)]
    values["cards_visibility"] = values["cards_visibility"] or [{"players": [i], "teams": []} for i in range(players)]
    # Automatically generated per-player defaults do not constitute changed rules.
    defaults = {"player_teams": lambda i: None, "dealer_players": lambda i: False,
                "personal_pile_counts": lambda i: values["personal_pile_count"],
                "cards_visibility": lambda i: {"players": [i], "teams": []},
                "personal_pile_settings": lambda i: [{"access": "owner", "ordered": False,
                    "order_by": "time", "new_card": "top", "size_order": "up"}
                    for _ in range(values["personal_pile_count"])],
                "player_names": lambda i: f"Player{i + 1}"}
    for key, default in defaults.items():
        while values[key] and values[key][-1] == default(len(values[key]) - 1):
            values[key].pop()
    return preset_values(values)

def configuration_info(settings):
    baseline = settings.get("configuration_baseline") or load_default_settings()
    return {"name": settings.get("configuration_name", "Default"),
            "modified": configuration_values(settings) != configuration_values(baseline)}
