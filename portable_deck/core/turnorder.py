"""Optional manual turn destinations, independent of any specific card game."""
from dataclasses import dataclass
from .actionerrors import ActionValidationError


def next_player_error(game, player):
    if not game.allow_choose_next_player:
        return ActionValidationError("action_disabled", "Choosing the next player is disabled.")
    if not isinstance(player, int) or isinstance(player, bool) or not 0 <= player < len(game.players):
        return ActionValidationError("invalid_target", "Choose a valid next player.")
    if player in game.left_players:
        return ActionValidationError("target_left", "The chosen player has left the session.")
    return None


@dataclass(frozen=True)
class NextPlayer:
    index: int
    name: str


@dataclass(frozen=True)
class NextPlayerOptions:
    allowed: bool
    reason: str
    code: str
    players: tuple[NextPlayer, ...]


def build_next_player_options(game):
    available = game.session.end_turn_availability()
    players = tuple(NextPlayer(i, game.players[i].name) for i in game.active_player_indices())
    if not game.allow_choose_next_player:
        return NextPlayerOptions(False, "Choosing the next player is disabled.", "action_disabled", players)
    return NextPlayerOptions(available.allowed, available.reason, available.code, players)
