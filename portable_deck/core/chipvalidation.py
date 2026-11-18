"""Shared chip parameter validation for model and session callers."""
from .actionerrors import ActionValidationError as Error


def chip_action_error(game, action, player_index=None, amount=None):
    if not game.enable_chip_accounts:
        return Error("action_disabled", "Chip accounts are disabled.")
    if action in {"buy_chips", "take_pot"}:
        if (not isinstance(player_index, int) or isinstance(player_index, bool)
                or not 0 <= player_index < len(game.players)):
            return Error("invalid_target", "Choose a valid player to receive the pot." if action == "take_pot"
                         else "Choose a valid player to receive chips.")
    if action == "play_chips":
        if game.pending_pot_withdrawal is not None:
            return Error("pot_approval_pending", "Chip play is paused while the pot withdrawal is awaiting approval.")
        if not isinstance(amount, int) or isinstance(amount, bool):
            return Error("invalid_amount", f"The minimum bet is {game.minimum_bet} chips.")
        if amount < game.minimum_bet:
            return Error("minimum_bet_not_met", f"The minimum bet is {game.minimum_bet} chips.")
        if amount > game.chip_balance(game.current_player_index):
            return Error("insufficient_chips", f"{game.players[game.current_player_index].name} does not have enough chips.")
    elif action == "buy_chips":
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 1:
            return Error("invalid_amount", "Enter a positive whole number of chips.")
    elif action == "take_pot":
        if game.chip_pot < 1:
            return Error("empty_pot", "There are no chips in the pot.")
        if game.pending_pot_withdrawal is not None:
            return Error("pot_approval_pending", "A pot withdrawal request is already waiting for approval.")
    else:
        raise ValueError(f"Unknown chip action: {action}")
    return None
