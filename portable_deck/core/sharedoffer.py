"""Public card draft with one choice for each active player."""
import copy
from dataclasses import dataclass
from .actionerrors import ActionValidationError


@dataclass(frozen=True)
class SharedOfferView:
    active: bool
    player: int | None = None
    player_name: str = ""
    cards: tuple[str, ...] = ()
    remaining_players: tuple[int, ...] = ()


def shared_offer_view(game):
    offer = game.pending_shared_offer
    if offer is None:
        return SharedOfferView(False)
    player = offer["players"][0]
    return SharedOfferView(True, player, game.players[player].name,
                           tuple(offer["cards"]), tuple(offer["players"]))


def restore_shared_offer(game, offer):
    if offer is None:
        return None
    if (not game.enable_special_actions or not game.allow_shared_offer or not isinstance(offer, dict)
            or set(offer) != {"cards", "players"}):
        raise ValueError("Invalid saved shared offer.")
    cards, players = offer["cards"], offer["players"]
    if (not isinstance(cards, list) or not cards or any(not isinstance(card, str) or not card for card in cards)
            or not isinstance(players, list) or len(players) != len(cards)
            or any(type(p) is not int or p not in game.active_player_indices() for p in players)
            or len(set(players)) != len(players)):
        raise ValueError("Invalid saved shared offer cards or participants.")
    return copy.deepcopy(offer)


def start_shared_offer(game):
    from .actionavailability import action_availability
    available = action_availability(game, "start_shared_offer")
    if not available.allowed:
        raise ActionValidationError(available.code, available.reason)
    players = game.active_player_indices()
    if game.turn_direction == -1:
        players = list(reversed(players))
    start = players.index(game.current_player_index)
    players = players[start:] + players[:start]
    cards = [game.deck.draw_card() for _ in players]
    if any(card is None for card in cards):
        raise ActionValidationError("action_rejected", "The shared offer could not be drawn.")
    game.pending_shared_offer = {"cards": cards, "players": players}
    game.log_action(game.players[game.current_player_index].name, "shared_offer_started", count=len(cards))
    return len(cards)


def choose_shared_offer(game, index):
    from .actionavailability import action_availability
    available = action_availability(game, "choose_shared_offer")
    if not available.allowed:
        raise ActionValidationError(available.code, available.reason)
    offer = game.pending_shared_offer
    if type(index) is not int or not 0 <= index < len(offer["cards"]):
        raise ActionValidationError("invalid_selection", "Choose an available offer card.")
    player = offer["players"].pop(0)
    card = offer["cards"].pop(index)
    game.players[player].draw_card(card)
    game.log_action(game.players[player].name, "shared_offer_chosen", card)
    if not offer["players"]:
        game.pending_shared_offer = None
    return player
