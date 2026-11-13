"""Named settings configurations, separate from saved game sessions."""
import copy
import json
import os
import warnings
from dataclasses import dataclass
from pathlib import Path
from .settings import CONFIG_DIR, DEFAULT_SETTINGS
from ..core.settingsvalidation import validate_settings, validate_structure, recover_settings

PRESETS_DIR = os.path.join(CONFIG_DIR, "presets")




@dataclass(frozen=True)
class PresetCompatibility:
    missing: tuple = ()
    unknown: tuple = ()
    wrong_types: tuple = ()

    @property
    def compatible(self):
        return not (self.missing or self.unknown or self.wrong_types)

    def message(self):
        lines = ["This preset has different input options from this version of Portable Deck."]
        if self.missing:
            lines.append("Missing options (application defaults will be used): " + ", ".join(self.missing))
        if self.unknown:
            lines.append("Unknown options (will be ignored): " + ", ".join(self.unknown))
        if self.wrong_types:
            lines.append("Options with invalid value types (will be replaced): " + ", ".join(self.wrong_types))
        return "\n\n".join(lines)


def preset_compatibility(values):
    """Compare rule inputs, excluding app preferences, player count and metadata."""
    from .configurationinfo import APP_SETTINGS, METADATA
    if not isinstance(values, dict):
        raise ValueError("The settings file must contain a settings object.")
    expected = set(DEFAULT_SETTINGS) - APP_SETTINGS - METADATA
    supplied = set(values) - APP_SETTINGS - METADATA
    unknown = set(supplied - expected)
    from ..core.interactions import INTERACTIONS
    nested = {
        "interaction_options": set(INTERACTIONS),
        "leave_conditions": {"match", "own_score", "own_score_at", "opponent_score", "opponent_score_at", "no_chips", "any_time"},
    }
    for key, options in nested.items():
        if isinstance(values.get(key), dict):
            unknown.update(f"{key}.{option}" for option in values[key] if option not in options)
    return PresetCompatibility(
        tuple(sorted(expected - supplied)), tuple(sorted(unknown)),
        tuple(sorted(key for key in expected & supplied
                     if type(values[key]) is not type(DEFAULT_SETTINGS[key]))))


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


def read_preset(path, current_settings=None, on_warning=None):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    from .configurationinfo import APP_SETTINGS, preset_values, configuration_values
    raw = data.get("settings", data) if isinstance(data, dict) else data
    if not isinstance(raw, dict):
        raise ValueError("The settings file must contain a settings object.")
    compatibility = preset_compatibility(raw)
    notices = [compatibility.message()] if not compatibility.compatible else []
    current = current_settings or DEFAULT_SETTINGS
    filtered = {key: copy.deepcopy(value) for key, value in raw.items() if key not in APP_SETTINGS}
    from ..core.interactions import INTERACTIONS
    leave_keys = {"match", "own_score", "own_score_at", "opponent_score", "opponent_score_at", "no_chips", "any_time"}
    for key, known in (("interaction_options", INTERACTIONS), ("leave_conditions", leave_keys)):
        if isinstance(filtered.get(key), dict):
            filtered[key] = {option: value for option, value in filtered[key].items() if option in known}
    structured, corrections = recover_settings(filtered, structure_only=True)
    notices.extend(corrections)
    merged = preset_values(structured)
    merged.update({key: copy.deepcopy(current.get(key, DEFAULT_SETTINGS[key])) for key in APP_SETTINGS})
    merged = validate_structure(merged)
    count = merged["num_players"]
    if not 1 <= count <= 20:
        raise ValueError("Player count must be between 1 and 20.")
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
    if merged["team_count"] > count:
        notices.append(f"team_count: reduced to {count} to fit the current player count.")
    merged["team_count"] = min(merged.get("team_count", 1), count)
    regular = merged["team_count"] - int(merged.get("enable_dealer", False)) if merged.get("enable_teams", False) else 0
    valid = {f"team_{i + 1}" for i in range(regular)}
    if merged.get("enable_dealer", False):
        valid.add("dealer")
    if any(team is not None and team not in valid for team in merged["player_teams"]):
        notices.append("player_teams: invalid team assignments were skipped.")
    merged["player_teams"] = [team if team in valid else None for team in merged.get("player_teams", [])]
    settings, corrections = recover_settings(merged)
    notices.extend(corrections)
    settings["configuration_name"] = data.get("name", Path(path).stem)
    settings["configuration_baseline"] = configuration_values(settings)
    if notices:
        text = "\n\n".join(notices)
        if on_warning is not None:
            on_warning(text)
        else:
            warnings.warn(text, UserWarning, stacklevel=2)
    return settings
