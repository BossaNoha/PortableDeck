"""Serialization helpers for saving and restoring game sessions."""
import copy

from .deck import Deck
from .player import Player


def export_session(game):
    """Return independent data containing the complete resumable game state."""
    state = {
        "enable_team_pile_access": game.enable_team_pile_access,
        "enable_dealer_pile_access": game.enable_dealer_pile_access,
        "enable_flipping": game.enable_flipping, "allow_flip_hand": game.allow_flip_hand,
        "allow_flip_table": game.allow_flip_table, "allow_flip_player_cards": game.allow_flip_player_cards,
        "limit_table_rows": game.limit_table_rows, "limit_table_columns": game.limit_table_columns,
        "enable_table_limits": game.enable_table_limits,
        "max_table_rows": game.max_table_rows, "max_table_columns": game.max_table_columns,
        "enable_special_actions": game.enable_special_actions,
        "allow_insert_draw_deck": game.allow_insert_draw_deck,
        "allow_insert_discard_pile": game.allow_insert_discard_pile,
        "reset_chip_accounts_on_restart": game.reset_chip_accounts_on_restart,
        "enable_player_return": game.enable_player_return,
        "enable_player_leaving": game.enable_player_leaving, "leave_conditions": game.leave_conditions,
        "left_players": game.left_players,
        "enable_target_score": game.enable_target_score, "target_score": game.target_score,
        "enable_score_warning": game.enable_score_warning, "score_warning": game.score_warning,
        "score_alerts_seen": game.score_alerts_seen,
        "allow_reduce_score": game.allow_reduce_score,
        "configuration_info": game.configuration_info,
        "enable_cards_visibility": game.enable_cards_visibility,
        "cards_visibility": game.cards_visibility,
        "enable_interactions": game.enable_interactions,
        "interaction_options": game.interaction_options,
        "share_team_chips": game.share_team_chips,
        "share_team_score": game.share_team_score,
        "enable_team_score": game.enable_team_score,
        "team_scores": game.team_scores,
        "enable_roles_teams": game.enable_roles_teams,
        "enable_dealer": game.enable_dealer,
        "enable_teams": game.enable_teams,
        "team_count": game.team_count,
        "team_names": game.team_names,
        "player_teams": game.player_teams,
        "dealer_players": game.dealer_players,
        "enable_personal_piles": game.enable_personal_piles,
        "personal_pile_count": game.personal_pile_count,
        "unequal_personal_piles": game.unequal_personal_piles,
        "personal_pile_counts": game.personal_pile_counts,
        "personal_pile_settings": game.personal_pile_settings,
        "personal_piles": game.personal_piles,
        "enable_table": game.enable_table,
        "allow_choose_next_player": game.allow_choose_next_player,
        "allow_reverse_turn_order": game.allow_reverse_turn_order,
        "allow_skip_next_player": game.allow_skip_next_player,
        "allow_play_multiple_cards": game.allow_play_multiple_cards,
        "turn_direction": game.turn_direction,
        "enable_discard_pile": game.enable_discard_pile,
        "deck_path": game.deck.path,
        "deck_types": game.deck.types,
        "deck_cards": game.deck.cards,
        "remaining_deck": game.deck.flat_deck,
        "players": [{"name": player.name, "revealed_indices": sorted(player.revealed_indices), "hand": player.hand} for player in game.players],
        "discard_pile": game.discard_pile,
        "discard_piles": game.discard_piles,
        "personal_discard_piles": game.personal_discard_piles,
        "shared_discard_pile_count": game.shared_discard_pile_count,
        "personal_discard_pile_count": game.personal_discard_pile_count,
        "table_cards": game.table_cards,
        "current_player_index": game.current_player_index,
        "history": game.history,
        "game_log": game.game_log,
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
    return copy.deepcopy(state)


def restore_session(game_class, state):
    """Restore independent game state without accessing session or deck files."""
    state = copy.deepcopy(state)
    game = game_class.__new__(game_class)
    game.allow_choose_next_player = state.get("allow_choose_next_player", False)
    if not isinstance(game.allow_choose_next_player, bool):
        raise ValueError("Saved allow_choose_next_player must be true or false")
    game.allow_reverse_turn_order = state.get("allow_reverse_turn_order", False)
    if not isinstance(game.allow_reverse_turn_order, bool):
        raise ValueError("Saved allow_reverse_turn_order must be true or false")
    game.allow_skip_next_player = state.get("allow_skip_next_player", False)
    if not isinstance(game.allow_skip_next_player, bool):
        raise ValueError("Saved allow_skip_next_player must be true or false")
    game.allow_play_multiple_cards = state.get("allow_play_multiple_cards", False)
    if not isinstance(game.allow_play_multiple_cards, bool):
        raise ValueError("Saved allow_play_multiple_cards must be true or false")
    game.turn_direction = state.get("turn_direction", 1)
    if type(game.turn_direction) is not int or game.turn_direction not in (-1, 1):
        raise ValueError("Saved turn_direction must be 1 or -1")
    if not game.allow_reverse_turn_order and game.turn_direction != 1:
        raise ValueError("Reverse direction requires allow_reverse_turn_order")
    game.enable_table = state.get("enable_table", True)
    game.enable_discard_pile = state.get("enable_discard_pile", True)
    original_deck = {"types": state.get("deck_types"), "cards": state.get("deck_cards")}
    game.deck = Deck.from_definition(original_deck, path=state.get("deck_path"))
    game.deck.flat_deck = state["remaining_deck"]
    game.players = []
    for saved_player in state["players"]:
        player = Player(saved_player["name"])
        player.revealed_indices = set(saved_player.get("revealed_indices", []))
        player.hand = saved_player["hand"]
        game.players.append(player)
    if not game.players:
        raise ValueError("Saved game has no players")
    game.shared_discard_pile_count = state.get("shared_discard_pile_count", 1)
    game.personal_discard_pile_count = state.get("personal_discard_pile_count", 0)
    game.discard_piles = state.get("discard_piles", [state.get("discard_pile", [])])
    game.personal_discard_piles = state.get(
        "personal_discard_piles",
        [[] for _ in game.players],
    )
    game.ensure_discard_pile_state()
    game.table_cards = state.get("table_cards", [])
    game.current_player_index = state["current_player_index"]
    if not 0 <= game.current_player_index < len(game.players):
        raise ValueError("Saved game has an invalid current player")
    game.history = state["history"]
    game.game_log = state.get("game_log", state.get("gui_log", []))
    game.cards_drawn_this_turn = state["cards_drawn_this_turn"]
    game.cards_per_player = state.get("cards_per_player")
    game.allow_reduce_score = state.get("allow_reduce_score", False)
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
    game.reset_chip_accounts_on_restart = state.get("reset_chip_accounts_on_restart", True)
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

    game.normalize_table_positions()

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
    legacy_count = game.personal_discard_pile_count
    game.initialize_personal_piles(
        state.get("enable_personal_piles", legacy_count > 0),
        state.get("personal_pile_count", legacy_count or 1),
        state.get("personal_pile_settings", []),
        state.get("unequal_personal_piles", False),
        state.get("personal_pile_counts"),
        state.get("enable_team_pile_access", False), state.get("enable_dealer_pile_access", False),
    )
    if "personal_piles" in state:
        game.personal_piles = state["personal_piles"]
    elif legacy_count:
        game.personal_piles = game.personal_discard_piles
        game.personal_discard_piles = [[] for _ in game.players]
        game.personal_discard_pile_count = 0
        game.ensure_discard_pile_state()
        for snapshot in game.undo_stack:
            snapshot["personal_piles"] = snapshot.get("personal_discard_piles", game.personal_piles)
            snapshot["personal_discard_piles"] = [[] for _ in game.players]
    if (not isinstance(game.personal_piles, list) or len(game.personal_piles) != len(game.players)
            or any(not isinstance(group, list) or len(group) != game.personal_pile_counts[owner]
                   or any(not isinstance(pile, list) or any(not isinstance(card, str) for card in pile)
                          for pile in group) for owner, group in enumerate(game.personal_piles))):
        raise ValueError("Saved personal piles do not match the player and pile counts.")
    game.initialize_roles_teams(state.get("enable_roles_teams", False), state.get("enable_dealer", False),
                                state.get("enable_teams", False), state.get("team_count", 1),
                                state.get("team_names", []), state.get("player_teams"), state.get("dealer_players"))
    game.initialize_cards_visibility(state.get("enable_cards_visibility", False), state.get("cards_visibility", []))
    game.initialize_interactions(state.get("enable_interactions", False), state.get("interaction_options", {}))
    game.initialize_team_resources(state.get("share_team_chips", False), state.get("share_team_score", False), state.get("enable_team_score", False))
    game.team_scores.update(state.get("team_scores", {}))
    game.initialize_table_limits(state.get("enable_table_limits", False), state.get("max_table_rows", 3), state.get("max_table_columns", 5), state.get("limit_table_rows", True), state.get("limit_table_columns", True))
    game.initialize_flipping(state.get("enable_flipping", False), state.get("allow_flip_hand", False),
                             state.get("allow_flip_table", False), state.get("allow_flip_player_cards", False))
    game.initialize_special_actions(state.get("enable_special_actions", False), state.get("allow_insert_draw_deck", False), state.get("allow_insert_discard_pile", False))
    game.initialize_leaving(state.get("enable_player_leaving", False), state.get("leave_conditions", {}), state.get("enable_player_return", False))
    game.left_players = state.get("left_players", [])
    if any(not isinstance(i, int) or isinstance(i, bool) or not 0 <= i < len(game.players) for i in game.left_players):
        raise ValueError("Invalid departed player index.")
    game.initialize_score_limits(state.get("enable_target_score", False), state.get("target_score", 100),
                                 state.get("enable_score_warning", False), state.get("score_warning", 80))
    game.score_alerts_seen = state.get("score_alerts_seen", {})
    game.configuration_info = state.get("configuration_info", {"name": "Unknown", "modified": None})
    game.apply_feature_settings()
    game.ensure_initial_log()
    return game
