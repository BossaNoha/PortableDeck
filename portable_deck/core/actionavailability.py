"""GUI-independent action availability for graphical and command-line clients.

Card indices are zero-based. This API only inspects state; it never executes actions.
"""
from dataclasses import dataclass
from .interactions import INTERACTIONS


@dataclass(frozen=True)
class ActionContext:
    hand_index: int | None = None
    table_index: int | None = None
    target_position: tuple[int, int] | None = None
    owner: int | None = None
    pile_index: int | None = None


@dataclass(frozen=True)
class ActionAvailability:
    allowed: bool
    reason: str = ""
    code: str = ""


ACTIONS = frozenset((
    "play_cards", "reverse_turn_order", "draw_card", "discard_card", "play_card", "play_face_down", "play_personal_pile", "take_personal_pile", "swap_table_card",
    "flip_hand_card", "play_at_position", "take_table_card", "discard_table_card",
    "flip_table_card", "move_table_card", "request_point", "reduce_score",
    "draw_from_discard", "recycle_discard", "clear_table", "leave_session",
    "buy_chips", "play_chips", "take_pot", "insert_draw_deck", "insert_discard_pile",
)) | frozenset(INTERACTIONS)


def action_availability(game, action, context=None):
    if action not in ACTIONS:
        raise ValueError(f"Unknown action: {action}")
    return _evaluate_availability(game, action, context or ActionContext())


def _evaluate_availability(g, action, context):
    enabled = {
        "play_cards": g.enable_table and g.allow_play_multiple_cards,
        "reverse_turn_order": g.allow_reverse_turn_order,
        "draw_card": True,
        "discard_card": g.enable_discard_pile,
        "play_card": g.enable_table or (not g.enable_discard_pile and not g.enable_interactions),
        "swap_table_card": g.enable_table and g.allow_positioned_play and g.occupied_slot_action == "swap",
        "play_face_down": g.enable_table and g.allow_face_down_table_cards,
        "play_personal_pile": g.enable_table and g.enable_personal_piles,
        "take_personal_pile": g.enable_table and g.enable_personal_piles,
        "flip_hand_card": g.enable_flipping and g.allow_flip_hand,
        "play_at_position": g.enable_table and (g.allow_positioned_play or g.allow_play_in_front_of_players),
        "take_table_card": g.enable_table and g.allow_take_from_table,
        "discard_table_card": g.enable_table and g.enable_discard_pile and g.allow_move_table_card_to_discard,
        "flip_table_card": g.can_flip_table_cards(),
        "move_table_card": g.enable_table and g.allow_move_cards_on_table,
        "request_point": g.score_enabled,
        "reduce_score": g.score_enabled and g.allow_reduce_score,
        "draw_from_discard": g.enable_discard_pile and g.allow_draw_from_discard,
        "recycle_discard": g.enable_discard_pile and g.allow_recycle_discard_to_deck,
        "clear_table": g.enable_table and g.allow_manual_table_cleanup and g.enable_discard_pile,
        "leave_session": g.enable_player_leaving,
        "buy_chips": g.enable_chip_accounts, "play_chips": g.enable_chip_accounts, "take_pot": g.enable_chip_accounts,
        "insert_draw_deck": g.enable_special_actions and g.allow_insert_draw_deck,
        "insert_discard_pile": g.enable_special_actions and g.allow_insert_discard_pile and g.enable_discard_pile,
    }
    enabled.update({key: g.interaction_allowed(key) for key in INTERACTIONS})
    if not enabled[action]:
        return ActionAvailability(False, "This action is disabled by the game rules.", "action_disabled")
    if not g.active_player_indices():
        return ActionAvailability(False, "All players have left. Return a player or restart the game.", "no_active_players")
    if g.current_player_index in g.left_players:
        return ActionAvailability(False, "This player has left the session.", "player_left")
    if action == "swap_table_card":
        for index, cards, message in (
            (context.hand_index, g.players[g.current_player_index].hand, "Select an available card in your hand."),
            (context.table_index, g.table_cards, "Select an available card on the table."),
        ):
            if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(cards):
                return ActionAvailability(False, message, "invalid_selection")
    if g.current_player_must_confirm_point() or g.current_player_must_confirm_pot_withdrawal():
        return ActionAvailability(False, "Complete the pending confirmation first.", "confirmation_required")
    if action == "play_cards" and len(g.players[g.current_player_index].hand) < 2:
        return ActionAvailability(False, "At least two hand cards are needed.", "not_enough_cards")
    if action in {"play_personal_pile", "take_personal_pile"}:
        if context.owner is not None or context.pile_index is not None:
            owner, pile = context.owner, context.pile_index
            if (not isinstance(owner, int) or isinstance(owner, bool)
                    or not isinstance(pile, int) or isinstance(pile, bool)
                    or not 0 <= owner < len(g.players)
                    or not 0 <= pile < len(g.personal_piles[owner])):
                return ActionAvailability(False, "Choose a valid personal pile.", "invalid_pile")
            if not g.can_access_personal_pile(owner, pile):
                return ActionAvailability(False, "You cannot access this personal pile.", "access_denied")
            if action == "take_personal_pile" and not g.personal_piles[owner][pile]:
                return ActionAvailability(False, "This personal pile is empty.", "empty_pile")
    if action in {"request_point", "reduce_score"} and g.pending_point_request:
        return ActionAvailability(False, "Wait for the other players to confirm the previous score change.", "score_approval_pending")
    if action in {"play_chips", "take_pot"} and g.pending_pot_withdrawal:
        return ActionAvailability(False, "Wait for the pending pot withdrawal to be approved.", "pot_approval_pending")
    if action == "play_chips" and g.chip_balance(g.current_player_index) < g.minimum_bet:
        return ActionAvailability(False, f"Minimum bet: {g.minimum_bet} chips. Available: {g.chip_balance(g.current_player_index)}.", "insufficient_chips")
    if action == "take_pot" and g.chip_pot == 0:
        return ActionAvailability(False, "The pot is empty.", "empty_pot")
    if action == "draw_card" and not g.deck.flat_deck:
        return ActionAvailability(False, "The draw deck is empty.", "empty_deck")
    discard_piles = list(g.discard_piles) + [pile for player_piles in g.personal_discard_piles for pile in player_piles]
    if action == "draw_from_discard" and not any(discard_piles):
        return ActionAvailability(False, "All discard piles are empty.", "empty_discard")
    if action == "recycle_discard":
        if g.deck.flat_deck:
            return ActionAvailability(False, "The draw deck must be empty before recycling.", "deck_not_empty")
        if not any(discard_piles):
            return ActionAvailability(False, "There are no discarded cards to recycle.", "empty_discard")
    if action == "clear_table" and not g.table_cards:
        return ActionAvailability(False, "The table is empty.", "empty_table")
    if action == "leave_session" and not g.can_leave_session():
        if g.pending_point_request or g.pending_pot_withdrawal:
            return ActionAvailability(False, "Complete the pending confirmation before leaving.", "confirmation_required")
        rule = g.leave_conditions
        details = []
        for key, label in (("own_score", "Your score"), ("opponent_score", "An opponent's score")):
            if rule[key] and g.score_enabled and g.enable_target_score:
                threshold = g.score_warning if rule[key + "_at"] == "warning" else g.target_score
                suffix = f" Current personal score: {g.scores[g.current_player_index]}." if key == "own_score" else ""
                details.append(f"{label} must reach {threshold}.{suffix}")
        if rule["no_chips"] and g.enable_chip_accounts:
            details.append(f"Your chip account must be empty. Available: {g.chip_balance(g.current_player_index)}.")
        return ActionAvailability(False, ("All conditions required. " if rule["match"] == "all" else "At least one condition required. ") + " ".join(details), "leave_conditions_not_met")
    hand_actions = {"play_card", "discard_card", "play_face_down", "play_personal_pile", "flip_hand_card", "play_at_position", "give_card"}
    if (action in hand_actions or action in {"insert_draw_deck", "insert_discard_pile"}) and context.hand_index is None:
        return ActionAvailability(False, "Select a card in your hand first.", "selection_required")
    if action in {"take_table_card", "discard_table_card", "flip_table_card", "move_table_card"} and context.table_index is None:
        return ActionAvailability(False, "Select a card on the table first.", "selection_required")
    if action in hand_actions | {"insert_draw_deck", "insert_discard_pile"}:
        if not isinstance(context.hand_index, int) or isinstance(context.hand_index, bool) or not 0 <= context.hand_index < len(g.players[g.current_player_index].hand):
            return ActionAvailability(False, "The selected hand card is no longer available.", "invalid_selection")
    if action in {"take_table_card", "discard_table_card", "flip_table_card", "move_table_card"}:
        if not isinstance(context.table_index, int) or isinstance(context.table_index, bool) or not 0 <= context.table_index < len(g.table_cards):
            return ActionAvailability(False, "The selected table card is no longer available.", "invalid_selection")
    if action in {"play_at_position", "move_table_card"} and context.target_position is None:
        return ActionAvailability(False, "Select an empty target position on the table.", "target_required")
    if action in {"play_at_position", "move_table_card"} and context.target_position is not None:
        position = context.target_position
        if (not isinstance(position, (tuple, list)) or len(position) != 2
                or any(not isinstance(value, int) or isinstance(value, bool) for value in position)
                or tuple(position) not in g.available_table_positions()):
            return ActionAvailability(False, "The target position is occupied or outside the available table positions.", "invalid_target")
    if action in {"play_cards", "play_card", "play_face_down"} and g.enable_table and not g.available_table_positions():
        return ActionAvailability(False, "The table has no empty positions within its limits.", "table_full")
    if action == "play_card" and context.target_position is not None:
        position = context.target_position
        if (not isinstance(position, (tuple, list)) or len(position) != 2
                or any(not isinstance(value, int) or isinstance(value, bool) for value in position)
                or not g.enable_table or tuple(position) != tuple(g.default_table_position())):
            return ActionAvailability(False, "Choose the default table position.", "invalid_target")
    return ActionAvailability(True)


@dataclass(frozen=True)
class DropAvailability:
    action: str | None
    availability: ActionAvailability
    target_position: tuple[int, int] | None = None


def drop_availability(game, source, index, position=None):
    """Resolve a proposed drop and check it through the shared action rules."""
    if not game.enable_table:
        return DropAvailability(None, ActionAvailability(False, "The table is disabled.", "action_disabled"))
    if position is not None and (not isinstance(position, (tuple, list)) or len(position) != 2
            or any(not isinstance(value, int) or isinstance(value, bool) for value in position)):
        return DropAvailability(None, ActionAvailability(False, "Choose a valid table position.", "invalid_target"))
    if source == "hand":
        action = "play_at_position" if game.allow_positioned_play or game.allow_play_in_front_of_players else "play_card"
        if action == "play_card":
            position = game.default_table_position() if game.available_table_positions() else None
    elif source == "table":
        action = "move_table_card"
    else:
        return DropAvailability(None, ActionAvailability(False, "Choose a hand or table card.", "invalid_selection"))
    context = ActionContext(hand_index=index, table_index=index, target_position=position)
    return DropAvailability(action, action_availability(game, action, context),
                            tuple(position) if position is not None else None)


def available_move_targets(game, table_index):
    """Return only positions passing the shared move availability check."""
    return tuple(position for position in sorted(game.available_table_positions())
                 if action_availability(game, "move_table_card",
                     ActionContext(table_index=table_index, target_position=position)).allowed)
