"""GUI-independent action availability for graphical and command-line clients.

Card indices are zero-based. This API only inspects state; it never executes actions.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ActionContext:
    hand_index: int | None = None
    table_index: int | None = None
    target_position: tuple[int, int] | None = None


@dataclass(frozen=True)
class ActionAvailability:
    allowed: bool
    reason: str = ""


ACTIONS = frozenset((
    "draw_card", "discard_card", "play_card", "play_face_down", "play_personal_pile",
    "flip_hand_card", "play_at_position", "take_table_card", "discard_table_card",
    "flip_table_card", "move_table_card", "request_point", "reduce_score",
    "draw_from_discard", "recycle_discard", "clear_table", "leave_session",
    "buy_chips", "play_chips", "take_pot", "insert_draw_deck", "insert_discard_pile",
))


def action_availability(game, action, context=None):
    if action not in ACTIONS:
        raise ValueError(f"Unknown action: {action}")
    reason = _action_reason(game, action, context or ActionContext())
    return ActionAvailability(allowed=not reason, reason=reason)


def _action_reason(g, action, context):
    enabled = {
        "draw_card": True,
        "discard_card": g.enable_discard_pile,
        "play_card": g.enable_table or (not g.enable_discard_pile and not g.enable_interactions),
        "play_face_down": g.enable_table and g.allow_face_down_table_cards,
        "play_personal_pile": g.enable_table and g.enable_personal_piles,
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
    if not enabled[action]:
        return "This action is disabled by the game rules."
    if not g.active_player_indices():
        return "All players have left. Return a player or restart the game."
    if g.current_player_must_confirm_point() or g.current_player_must_confirm_pot_withdrawal():
        return "Complete the pending confirmation first."
    if action in {"request_point", "reduce_score"} and g.pending_point_request:
        return "Wait for the other players to confirm the previous score change."
    if action in {"play_chips", "take_pot"} and g.pending_pot_withdrawal:
        return "Wait for the pending pot withdrawal to be approved."
    if action == "play_chips" and g.chip_balance(g.current_player_index) < g.minimum_bet:
        return f"Minimum bet: {g.minimum_bet} chips. Available: {g.chip_balance(g.current_player_index)}."
    if action == "take_pot" and g.chip_pot == 0:
        return "The pot is empty."
    if action == "draw_card" and not g.deck.flat_deck:
        return "The draw deck is empty."
    discard_piles = list(g.discard_piles) + [pile for player_piles in g.personal_discard_piles for pile in player_piles]
    if action == "draw_from_discard" and not any(discard_piles):
        return "All discard piles are empty."
    if action == "recycle_discard":
        if g.deck.flat_deck:
            return "The draw deck must be empty before recycling."
        if not any(discard_piles):
            return "There are no discarded cards to recycle."
    if action == "clear_table" and not g.table_cards:
        return "The table is empty."
    if action == "leave_session" and not g.can_leave_session():
        if g.pending_point_request or g.pending_pot_withdrawal:
            return "Complete the pending confirmation before leaving."
        rule = g.leave_conditions
        details = []
        for key, label in (("own_score", "Your score"), ("opponent_score", "An opponent's score")):
            if rule[key] and g.score_enabled and g.enable_target_score:
                threshold = g.score_warning if rule[key + "_at"] == "warning" else g.target_score
                suffix = f" Current personal score: {g.scores[g.current_player_index]}." if key == "own_score" else ""
                details.append(f"{label} must reach {threshold}.{suffix}")
        if rule["no_chips"] and g.enable_chip_accounts:
            details.append(f"Your chip account must be empty. Available: {g.chip_balance(g.current_player_index)}.")
        return ("All conditions required. " if rule["match"] == "all" else "At least one condition required. ") + " ".join(details)
    hand_actions = {"play_card", "discard_card", "play_face_down", "play_personal_pile", "flip_hand_card", "play_at_position"}
    if (action in hand_actions or action in {"insert_draw_deck", "insert_discard_pile"}) and context.hand_index is None:
        return "Select a card in your hand first."
    if action in {"take_table_card", "discard_table_card", "flip_table_card", "move_table_card"} and context.table_index is None:
        return "Select a card on the table first."
    if action in hand_actions | {"insert_draw_deck", "insert_discard_pile"}:
        if not isinstance(context.hand_index, int) or isinstance(context.hand_index, bool) or not 0 <= context.hand_index < len(g.players[g.current_player_index].hand):
            return "The selected hand card is no longer available."
    if action in {"take_table_card", "discard_table_card", "flip_table_card", "move_table_card"}:
        if not isinstance(context.table_index, int) or isinstance(context.table_index, bool) or not 0 <= context.table_index < len(g.table_cards):
            return "The selected table card is no longer available."
    if action in {"play_at_position", "move_table_card"} and context.target_position is None:
        return "Select an empty target position on the table."
    if action in {"play_at_position", "move_table_card"} and context.target_position is not None:
        position = context.target_position
        if (not isinstance(position, (tuple, list)) or len(position) != 2
                or any(not isinstance(value, int) or isinstance(value, bool) for value in position)
                or tuple(position) not in g.available_table_positions()):
            return "The target position is occupied or outside the available table positions."
    if action in {"play_card", "play_face_down"} and g.enable_table and not g.available_table_positions():
        return "The table has no empty positions within its limits."
    return ""
