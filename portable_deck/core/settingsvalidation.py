"""Shared settings validation. No widgets or presentation dependencies."""
import copy
import inspect
from pathlib import Path
from .settingsschema import DEFAULT_SETTINGS
from .game import Game


def resolve_deck_path(path):
    return str(Path(__file__).resolve().parents[2] / path)



class SettingsValidationError(ValueError):
    """A validation failure with the affected fields for tolerant importers."""
    def __init__(self, message, *fields):
        super().__init__(message)
        self.fields = fields


def invalid(message, *fields):
    raise SettingsValidationError(message, *fields)

def validate_structure(values):
    if not isinstance(values, dict):
        raise ValueError("The settings file must contain a settings object.")
    settings = copy.deepcopy(DEFAULT_SETTINGS)
    settings.update({key: copy.deepcopy(value) for key, value in values.items() if key in DEFAULT_SETTINGS})
    for key, default in DEFAULT_SETTINGS.items():
        if type(settings[key]) is not type(default):
            invalid(f"Invalid value for {key}: expected {type(default).__name__}.", key)
    for key in ("player_names", "team_names"):
        if any(not isinstance(value, str) for value in settings[key]):
            invalid(f"{key} must contain names as text.", key)
    if any(type(value) is not bool for value in settings["dealer_players"]):
        invalid("Dealer flags must be true or false.", "dealer_players")
    if any(value is not None and not isinstance(value, str) for value in settings["player_teams"]):
        invalid("Team assignments must contain team identifiers or null.", "player_teams")
    if any(type(value) is not int or not 0 <= value <= 20 for value in settings["personal_pile_counts"]):
        invalid("Personal pile counts must be integers between 0 and 20.", "personal_pile_counts")
    for rule in settings["cards_visibility"]:
        if (not isinstance(rule, dict) or not isinstance(rule.get("players"), list)
                or not isinstance(rule.get("teams"), list)
                or any(type(i) is not int or i < 0 for i in rule["players"])
                or any(not isinstance(team, str) for team in rule["teams"])):
            invalid("Invalid hand visibility permissions.", "cards_visibility")
    for key in ("interaction_options",):
        if any(type(value) is not bool for value in settings[key].values()):
            invalid(f"{key} options must be true or false.", key)
    conditions = settings["leave_conditions"]
    for key in ("own_score", "opponent_score", "no_chips"):
        if key in conditions and type(conditions[key]) is not bool:
            invalid(f"Leaving condition {key} must be true or false.", "leave_conditions")
    if any(not isinstance(group, list) or any(not isinstance(rule, dict) for rule in group)
           for group in settings["personal_pile_settings"]):
        invalid("Invalid personal pile settings.", "personal_pile_settings")
    for group in settings["personal_pile_settings"]:
        for rule in group:
            if "ordered" in rule and type(rule["ordered"]) is not bool:
                invalid("Personal pile ordered must be true or false.", "personal_pile_settings")
    return settings


def validate_settings(values):
    if not isinstance(values, dict):
        raise ValueError("The settings file must contain a settings object.")
    settings = validate_structure(values)
    if not 1 <= settings["num_players"] <= 20:
        invalid("Player count must be between 1 and 20.", "num_players")
    if settings["cards_per_player"] < 0:
        invalid("Starting hand size must be non-negative.", "cards_per_player")
    if not 1 <= settings["autosave_count"] <= 1000:
        invalid("Autosaves to keep must be between 1 and 1000.", "autosave_count")
    for key, low, high in (("max_table_rows", 1, 20), ("max_table_columns", 1, 20),
                           ("shared_discard_pile_count", 1, 20), ("personal_pile_count", 1, 20)):
        if not low <= settings[key] <= high:
            invalid(f"{key} must be between {low} and {high}.", key)
    if settings["minimum_bet"] < 1:
        invalid("Minimum bet must be positive and starting balance non-negative.", "minimum_bet")
    if settings["starting_balance"] < 0:
        invalid("Minimum bet must be positive and starting balance non-negative.", "starting_balance")
    if settings["target_score"] < 1:
        invalid("Target score must be positive.", "target_score")
    if settings["score_warning"] < 0 or (settings["enable_target_score"] and settings["enable_score_warning"]
                                         and settings["score_warning"] >= settings["target_score"]):
        invalid("Warning score must be non-negative and below the target.", "score_warning")
    count = settings["num_players"]
    if not 1 <= settings["team_count"] <= count:
        invalid("The total team count, including Dealer, cannot exceed the player count.", "team_count")
    if any(not name.strip() for name in settings["team_names"]):
        invalid("Team names must be non-empty text.", "team_names")
    regular = settings["team_count"] - int(settings["enable_dealer"]) if settings["enable_teams"] else 0
    teams = {f"team_{i + 1}" for i in range(regular)} | {None, "dealer"}
    if settings["player_teams"] and (len(settings["player_teams"]) != count
                                    or any(team not in teams for team in settings["player_teams"])):
        invalid("Assign each player to an existing team or leave them unassigned.", "player_teams")
    if settings["dealer_players"] and len(settings["dealer_players"]) != count:
        invalid("Provide a dealer flag for each player.", "dealer_players")
    if settings["use_custom_player_names"] and (len(settings["player_names"]) != count
                                               or any(not name.strip() for name in settings["player_names"])):
        invalid("Enter a non-empty name for every player.", "player_names")
    if settings["unequal_personal_piles"] and len(settings["personal_pile_counts"]) != count:
        invalid("Provide a personal pile count for each player.", "personal_pile_counts")
    if not 0 <= settings["personal_discard_pile_count"] <= 20:
        invalid("Personal discard pile count must be between 0 and 20.", "personal_discard_pile_count")
    for key, allowed in (("draw_from_discard_mode", {"top", "any"}),
                         ("occupied_slot_action", {"invalid", "swap"})):
        if settings[key] not in allowed:
            invalid(f"Invalid option for {key}.", key)
    conditions = settings["leave_conditions"]
    if any(not isinstance(conditions.get(key, default), str) or conditions.get(key, default) not in allowed
           for key, default, allowed in (("match", "all", {"all", "any"}),
               ("own_score_at", "target", {"target", "warning"}),
               ("opponent_score_at", "target", {"target", "warning"}))):
        invalid("Invalid leaving condition.", "leave_conditions")
    for group in settings["personal_pile_settings"]:
        for rule in group:
            for key, default, allowed in (
                ("access", "owner", {"everyone", "team", "owner", "team_dealer", "dealer_only", "owner_dealer", "everyone_but_owner", "team_but_member"}),
                ("order_by", "time", {"time", "size"}), ("new_card", "top", {"top", "bottom"}),
                ("size_order", "up", {"up", "down"})):
                if not isinstance(rule.get(key, default), str) or rule.get(key, default) not in allowed:
                    invalid("Invalid personal pile settings.", "personal_pile_settings")
    if any(any(i >= count for i in rule["players"]) for rule in settings["cards_visibility"]):
        invalid("Invalid hand visibility permissions.", "cards_visibility")
    params = inspect.signature(Game).parameters
    args = {key: value for key, value in settings.items() if key in params}
    args.update(deck_path=resolve_deck_path(settings["deck_path"]),
                player_names=settings["player_names"] if settings["use_custom_player_names"] else None,
                score_enabled=settings["enable_score_counter"])
    # Older settings may have no explicit team assignments yet.
    args["player_teams"] = settings["player_teams"] or None
    args["dealer_players"] = settings["dealer_players"] or None
    try:
        game = Game(**args)
    except (OSError, ValueError) as error:
        # All non-deck constructor constraints are checked above.
        raise SettingsValidationError(str(error), "deck_path") from error
    if len(game.deck.flat_deck) < settings["num_players"] * settings["cards_per_player"]:
        invalid("The deck is too small for these settings.", "cards_per_player")
    return settings



def recover_settings(values, *, structure_only=False):
    """Skip invalid imported fields and return (valid settings, warning details).

    Direct form editing stays strict. Importers explicitly choose this tolerant
    path and must display its warnings. Unrelated valid fields are preserved.
    """
    candidate = copy.deepcopy(values)
    details = []
    validate = validate_structure if structure_only else validate_settings
    for _ in range(len(DEFAULT_SETTINGS) * 2):
        try:
            return validate(candidate), details
        except SettingsValidationError as error:
            if not error.fields:
                raise
            changed = False
            for key in error.fields:
                replacement = copy.deepcopy(DEFAULT_SETTINGS[key])
                count = candidate.get("num_players", DEFAULT_SETTINGS["num_players"])
                if key == "player_names" and candidate.get("use_custom_player_names"):
                    replacement = [f"Player{i + 1}" for i in range(count)]
                elif key == "personal_pile_counts" and candidate.get("unequal_personal_piles"):
                    replacement = [candidate.get("personal_pile_count", 1)] * count
                elif key == "score_warning":
                    replacement = min(DEFAULT_SETTINGS[key], candidate.get("target_score", 100) - 1)
                elif key == "cards_per_player" and candidate.get(key) == replacement:
                    # Even the normal starting hand may exceed a small valid deck.
                    replacement = 0
                if candidate.get(key) != replacement or type(candidate.get(key)) is not type(replacement):
                    candidate[key] = replacement
                    details.append(f"{key}: {error} Replacement: {replacement!r}.")
                    changed = True
            if not changed:
                raise
    raise ValueError("Could not recover a valid settings configuration.")
