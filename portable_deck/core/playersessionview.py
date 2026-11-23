"""Combined, immutable presentation snapshot for an explicitly chosen player."""
from dataclasses import dataclass
from .sharedoffer import SharedOfferView, shared_offer_view
from .sessionstatus import SessionStatus, build_session_status
from .playerview import (
    PlayerHandsView, PlayerTableView, PlayerPersonalPilesView, PlayerDiscardView,
    build_player_hands_view, build_player_table_view,
    build_player_personal_piles_view, build_player_discard_view,
)


@dataclass(frozen=True)
class PlayerSessionView:
    viewer: int
    status: SessionStatus
    hands: PlayerHandsView
    table: PlayerTableView
    personal_piles: PlayerPersonalPilesView
    discard: PlayerDiscardView
    shared_offer: SharedOfferView = SharedOfferView(False)


def build_player_session_view(game, viewer, hand_index=None):
    """Compose existing visibility rules without copying the authoritative model.

    hand_index is the optional local selection for personal-pile availability.
    The caller establishes viewer identity and builds this while the model is
    stable. This query does not provide authentication or concurrent locking.
    Internal history, logs, draw order, saved state and private action results
    are deliberately outside this presentation snapshot.
    """
    hands = build_player_hands_view(game, viewer)
    return PlayerSessionView(
        viewer, build_session_status(game), hands,
        build_player_table_view(game, viewer),
        build_player_personal_piles_view(game, viewer, hand_index),
        build_player_discard_view(game, viewer), shared_offer_view(game))
