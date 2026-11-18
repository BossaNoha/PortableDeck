"""Read-only, ordered work for the current player's turn entry."""
from dataclasses import dataclass
from .scorenotifications import ScoreNotification
from .chipnotifications import PotConfirmationNotification


@dataclass(frozen=True)
class TurnConfirmation:
    action: str
    notice: ScoreNotification | PotConfirmationNotification


@dataclass(frozen=True)
class TurnStartView:
    player: int
    active: bool
    notifications: tuple[ScoreNotification, ...]
    confirmations: tuple[TurnConfirmation, ...]

    @property
    def next_confirmation(self):
        return self.confirmations[0] if self.confirmations else None


def build_turn_start_view(game):
    """List score notices, then score approval, then pot approval.

    Display notices before explicitly acknowledging them. Requery after each
    decision and submit its action through the session controller. Never execute
    an entire saved queue: earlier decisions may change what remains required.
    """
    player = game.current_player_index
    if player not in game.active_player_indices():
        return TurnStartView(player, False, (), ())
    confirmations = []
    for action, notice in (("confirm_point", game.score_confirmation_notification()),
                           ("confirm_pot", game.pot_confirmation_notification())):
        if notice is not None:
            confirmations.append(TurnConfirmation(action, notice))
    return TurnStartView(player, True, tuple(game.score_notifications()), tuple(confirmations))
