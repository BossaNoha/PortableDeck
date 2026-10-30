"""Serialization helpers for saving and restoring game sessions."""
import json
import os

from .deck import Deck
from .player import Player


def save_session(game, path):
    """Save the complete state needed to continue a game later."""
    game.ensure_discard_pile_state()
    state = {
        "deck_path": game.deck.path,
        "deck_types": game.deck.types,
        "deck_cards": game.deck.cards,
        "remaining_deck": game.deck.flat_deck,
        "players": [{"name": player.name, "hand": player.hand} for player in game.players],
        "discard_pile": game.discard_pile,
        "discard_piles": game.discard_piles,
        "personal_discard_piles": game.personal_discard_piles,
        "shared_discard_pile_count": game.shared_discard_pile_count,
        "personal_discard_pile_count": game.personal_discard_pile_count,
        "table_cards": game.table_cards,
        "current_player_index": game.current_player_index,
        "history": game.history,
        "gui_log": game.gui_log,
        "cards_drawn_this_turn": game.cards_drawn_this_turn,
        "cards_per_player": game.cards_per_player,
        "score_enabled": game.score_enabled,
        "require_point_confirmation": game.require_point_confirmation,
        "scores": game.scores,
        "pending_point_request": game.pending_point_request,
        "allow_take_from_table": game.allow_take_from_table,
        "allow_move_table_card_to_discard": game.allow_move_table_card_to_discard,
        "allow_manual_table_cleanup": game.allow_manual_table_cleanup,
        "clear_table_on_round_end": game.clear_table_on_round_end,
        "allow_positioned_play": game.allow_positioned_play,
        "occupied_slot_action": game.occupied_slot_action,
        "enable_undo": game.enable_undo,
        "allow_move_cards_on_table": game.allow_move_cards_on_table,
        "allow_play_in_front_of_players": game.allow_play_in_front_of_players,
        "allow_draw_from_discard": game.allow_draw_from_discard,
        "draw_from_discard_mode": game.draw_from_discard_mode,
        "allow_face_down_table_cards": game.allow_face_down_table_cards,
        "allow_move_table_sequences": game.allow_move_table_sequences,
        "allow_recycle_discard_to_deck": game.allow_recycle_discard_to_deck,
        "enable_chip_accounts": game.enable_chip_accounts,
        "minimum_bet": game.minimum_bet,
        "starting_balance": game.starting_balance,
        "require_pot_withdrawal_confirmation": game.require_pot_withdrawal_confirmation,
        "chip_balances": game.chip_balances,
        "chip_pot": game.chip_pot,
        "pending_pot_withdrawal": game.pending_pot_withdrawal,
        "undo_stack": game.undo_stack,
    }
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    temporary_path = path + ".tmp"
    try:
        with open(temporary_path, "w", encoding="utf-8") as session_file:
            json.dump(state, session_file, indent=2)
        os.replace(temporary_path, path)
    except Exception:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)
        raise


def load_session(game_class, path):
    """Load a saved game and return an initialized instance of game_class."""
    with open(path, "r", encoding="utf-8") as session_file:
        state = json.load(session_file)

    game = game_class.__new__(game_class)
    game.deck = Deck(state["deck_path"])
    if "deck_types" in state and "deck_cards" in state:
        original_deck = {"types": state["deck_types"], "cards": state["deck_cards"]}
        Deck.validate_data(original_deck)
        game.deck.types = state["deck_types"]
        game.deck.cards = state["deck_cards"]
    game.deck.flat_deck = state["remaining_deck"]
    game.players = []
    for saved_player in state["players"]:
        player = Player(saved_player["name"])
        player.hand = saved_player["hand"]
        game.players.append(player)
    if not game.players:
        raise ValueError("Saved game has no players")
    game.shared_discard_pile_count = state.get("shared_discard_pile_count", 1)
    game.personal_discard_pile_count = state.get("personal_discard_pile_count", 0)
    game.discard_piles = state.get("discard_piles", [state.get("discard_pile", [])])
    if not game.discard_piles:
        game.discard_piles = [[]]
        game.shared_discard_pile_count = 1
    game.shared_discard_pile_count = len(game.discard_piles)
    game.personal_discard_piles = state.get(
        "personal_discard_piles",
        [[] for _ in game.players],
    )
    game.personal_discard_piles = [
        (list(piles) + [[] for _ in range(max(0, game.personal_discard_pile_count - len(piles)))])
        [:game.personal_discard_pile_count]
        for piles in game.personal_discard_piles[:len(game.players)]
    ]
    while len(game.personal_discard_piles) < len(game.players):
        game.personal_discard_piles.append([[] for _ in range(game.personal_discard_pile_count)])
    game.table_cards = state.get("table_cards", [])
    game.current_player_index = state["current_player_index"]
    if not 0 <= game.current_player_index < len(game.players):
        raise ValueError("Saved game has an invalid current player")
    game.history = state["history"]
    game.gui_log = state.get("gui_log", [])
    game.cards_drawn_this_turn = state["cards_drawn_this_turn"]
    game.cards_per_player = state.get("cards_per_player")
    game.score_enabled = state.get("score_enabled", False)
    game.require_point_confirmation = state.get("require_point_confirmation", False)
    game.scores = state.get("scores", [0 for _ in game.players])
    game.pending_point_request = state.get("pending_point_request")
    game.allow_take_from_table = state.get("allow_take_from_table", False)
    game.allow_move_table_card_to_discard = state.get("allow_move_table_card_to_discard", False)
    game.allow_manual_table_cleanup = state.get("allow_manual_table_cleanup", False)
    game.clear_table_on_round_end = state.get("clear_table_on_round_end", False)
    game.allow_positioned_play = state.get("allow_positioned_play", False)
    game.occupied_slot_action = state.get("occupied_slot_action", "invalid")
    game.enable_undo = state.get("enable_undo", False)
    game.allow_move_cards_on_table = state.get("allow_move_cards_on_table", False)
    game.allow_play_in_front_of_players = state.get("allow_play_in_front_of_players", False)
    game.allow_draw_from_discard = state.get("allow_draw_from_discard", False)
    saved_discard_mode = state.get("draw_from_discard_mode", "top")
    game.draw_from_discard_mode = saved_discard_mode if saved_discard_mode in {"top", "any"} else "top"
    game.allow_face_down_table_cards = state.get("allow_face_down_table_cards", False)
    game.allow_move_table_sequences = state.get("allow_move_table_sequences", False)
    game.allow_recycle_discard_to_deck = state.get("allow_recycle_discard_to_deck", False)
    # These options require positioned table state, including in older saves.
    game.allow_positioned_play = bool(
        game.allow_positioned_play or game.allow_face_down_table_cards or game.allow_move_table_sequences
    )
    game.allow_move_cards_on_table = bool(
        game.allow_move_cards_on_table or game.allow_move_table_sequences
    )
    game.enable_chip_accounts = state.get("enable_chip_accounts", False)
    game.minimum_bet = state.get("minimum_bet", 1)
    game.starting_balance = state.get("starting_balance", 100)
    game.require_pot_withdrawal_confirmation = state.get(
        "require_pot_withdrawal_confirmation", False
    )
    game.chip_balances = state.get(
        "chip_balances",
        [game.starting_balance if game.enable_chip_accounts else 0 for _ in game.players],
    )
    game.chip_pot = state.get("chip_pot", 0)
    game.pending_pot_withdrawal = state.get("pending_pot_withdrawal")
    game.undo_stack = state.get("undo_stack", [])

    if game.allow_positioned_play or game.allow_move_cards_on_table or game.allow_play_in_front_of_players:
        positions = [entry.get("position") for entry in game.table_cards]
        if not all(
            isinstance(position, (tuple, list))
            and len(position) == 2
            and all(isinstance(value, int) and not isinstance(value, bool) for value in position)
            for position in positions
        ):
            game.table_cards = [
                entry for _, entry in sorted(
                    enumerate(game.table_cards),
                    key=lambda pair: pair[1].get("position", pair[0])
                    if isinstance(pair[1].get("position", pair[0]), int)
                    else pair[0],
                )
            ]
            for index, entry in enumerate(game.table_cards):
                entry["position"] = [0, index]
        else:
            for entry in game.table_cards:
                entry["position"] = list(entry["position"])

    if game.cards_per_player is None:
        drawn = sum(
            entry.get("count", 0)
            for entry in game.history
            if entry.get("action") == "draw_multiple"
        ) + game.cards_drawn_this_turn
        cards_in_play = (
            sum(len(player.hand) for player in game.players)
            + sum(len(pile) for _, pile in game.all_discard_piles())
            + len(game.table_cards)
        )
        dealt_cards = cards_in_play - drawn
        game.cards_per_player = (
            dealt_cards // len(game.players)
            if dealt_cards >= 0 and dealt_cards % len(game.players) == 0
            else 0
        )
    return game
