"""Read-only chip approval prompts for any client."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PotConfirmationNotification:
    kind: str
    recipient: int
    requester: int
    beneficiary: int
    amount: int
    title: str
    message: str


def pot_confirmation_notification(game):
    """Prepare a prompt for the current eligible voter without changing state."""
    g = game
    if (not g.enable_chip_accounts or g.current_player_index not in g.active_player_indices()
            or not g.current_player_must_confirm_pot_withdrawal()):
        return None
    request = g.pending_pot_withdrawal
    requester, beneficiary = request["requester"], request["recipient"]
    voter = g.current_player_index
    return PotConfirmationNotification(
        "pot_approval", voter, requester, beneficiary, g.chip_pot,
        "Confirm pot withdrawal",
        f"{g.players[requester].name} requested to give the {g.chip_pot}-chip pot "
        f"to {g.players[beneficiary].name}.\n\nAs {g.players[voter].name}, do you approve?")
