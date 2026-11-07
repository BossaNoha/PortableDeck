"""Named settings configurations, separate from saved game sessions."""
import copy
import inspect
import json
import os
from pathlib import Path
from .settings import CONFIG_DIR, DEFAULT_SETTINGS, resolve_deck_path
from ..core.game import Game

PRESETS_DIR = os.path.join(CONFIG_DIR, "presets")


def validate_settings(values):
    if not isinstance(values, dict):
        raise ValueError("The settings file must contain a settings object.")
    settings = copy.deepcopy(DEFAULT_SETTINGS)
    settings.update({key: value for key, value in values.items() if key in DEFAULT_SETTINGS})
    for key, default in DEFAULT_SETTINGS.items():
        if type(settings[key]) is not type(default):
            raise ValueError(f"Invalid value for {key}.")
    if not 1 <= settings["num_players"] <= 20 or settings["cards_per_player"] < 0:
        raise ValueError("Invalid player count or starting hand size.")
    if not 1 <= settings["autosave_count"] <= 1000:
        raise ValueError("Autosaves to keep must be between 1 and 1000.")
    params = inspect.signature(Game).parameters
    args = {key: value for key, value in settings.items() if key in params}
    args.update(deck_path=resolve_deck_path(settings["deck_path"]),
                player_names=settings["player_names"] if settings["use_custom_player_names"] else None,
                score_enabled=settings["enable_score_counter"])
    # Older settings may have no explicit team assignments yet.
    args["player_teams"] = settings["player_teams"] or None
    args["dealer_players"] = settings["dealer_players"] or None
    game = Game(**args)
    if len(game.deck.flat_deck) < settings["num_players"] * settings["cards_per_player"]:
        raise ValueError("The deck is too small for these settings.")
    if settings["use_custom_player_names"] and any(not isinstance(name, str) or not name.strip() for name in settings["player_names"]):
        raise ValueError("Enter a non-empty name for every player.")
    if any(not isinstance(group, list) or any(not isinstance(rule, dict) for rule in group)
           for group in settings["personal_pile_settings"]):
        raise ValueError("Invalid personal pile settings.")
    return settings


def write_preset(path, settings):
    settings = validate_settings(settings)
    from .configurationinfo import preset_values
    settings = preset_values(settings)
    target = Path(path)
    temporary = target.with_name(target.name + ".tmp")
    try:
        temporary.write_text(json.dumps({"name": target.stem, "settings": settings}, indent=2), encoding="utf-8")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def read_preset(path, current_settings=None):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    from .configurationinfo import APP_SETTINGS, preset_values, configuration_values
    raw = data.get("settings", data) if isinstance(data, dict) else data
    if not isinstance(raw, dict):
        raise ValueError("The settings file must contain a settings object.")
    current = current_settings or DEFAULT_SETTINGS
    merged = preset_values(raw)
    merged.update({key: copy.deepcopy(current.get(key, DEFAULT_SETTINGS[key])) for key in APP_SETTINGS})
    count = merged["num_players"]
    for key, default in (("player_names", None), ("player_teams", None), ("dealer_players", False),
                         ("personal_pile_counts", merged.get("personal_pile_count", 1))):
        values = merged.get(key, [])
        if values:
            merged[key] = (values[:count] + [f"Player{i + 1}" if key == "player_names" else default
                                           for i in range(len(values), count)])
    merged["personal_pile_settings"] = merged.get("personal_pile_settings", [])[:count]
    visibility = merged.get("cards_visibility", [])[:count]
    for rule in visibility:
        rule["players"] = [i for i in rule["players"] if i < count]
    merged["cards_visibility"] = visibility
    merged["team_count"] = min(merged.get("team_count", 1), count)
    regular = merged["team_count"] - int(merged.get("enable_dealer", False)) if merged.get("enable_teams", False) else 0
    valid = {f"team_{i + 1}" for i in range(regular)}
    if merged.get("enable_dealer", False):
        valid.add("dealer")
    merged["player_teams"] = [team if team in valid else None for team in merged.get("player_teams", [])]
    settings = validate_settings(merged)
    settings["configuration_name"] = data.get("name", Path(path).stem)
    settings["configuration_baseline"] = configuration_values(settings)
    return settings
