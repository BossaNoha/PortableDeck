"""Immutable card projections containing only identities visible to a player."""
from dataclasses import dataclass
from .actionavailability import ActionContext, ActionAvailability, action_availability


@dataclass(frozen=True)
class CardView:
    index: int
    card: str | None
    revealed: bool


@dataclass(frozen=True)
class HandView:
    owner: int
    name: str
    fully_visible: bool
    cards: tuple[CardView, ...]

    @property
    def visible(self):
        return self.fully_visible or any(slot.card is not None for slot in self.cards)


@dataclass(frozen=True)
class PlayerHandsView:
    viewer: int
    viewer_name: str
    hands: tuple[HandView, ...]


def _validate_viewer(game, viewer):
    if (not isinstance(viewer, int) or isinstance(viewer, bool)
            or not 0 <= viewer < len(game.players)):
        raise ValueError("Choose a valid viewing player.")


def build_player_hands_view(game, viewer):
    """Project hands for an explicit player; hidden identities are never copied.

    This is a presentation query, not authentication of a remote caller.
    """
    _validate_viewer(game, viewer)
    hands = []
    for owner, player in enumerate(game.players):
        full = game.can_view_hand(viewer, owner)
        cards = tuple(CardView(i, card if full or i in player.revealed_indices else None,
                               i in player.revealed_indices)
                      for i, card in enumerate(player.hand))
        hands.append(HandView(owner, player.name, full, cards))
    return PlayerHandsView(viewer, game.players[viewer].name, tuple(hands))


@dataclass(frozen=True)
class TableCardView:
    index: int
    card: str | None
    player: str
    position: tuple[int, int]
    face_up: bool


@dataclass(frozen=True)
class PlayerTableView:
    viewer: int
    enabled: bool
    player_lanes: bool
    player_names: tuple[str, ...]
    cards: tuple[TableCardView, ...]
    available_positions: tuple[tuple[int, int], ...]


def build_player_table_view(game, viewer):
    """Hide face-down identities from every viewer, including their owner.

    Indices retain their model meaning even when cards share a position.
    A disabled table exposes no cards or targets.
    """
    _validate_viewer(game, viewer)
    cards = tuple(TableCardView(
        i, entry["card"] if entry.get("face_up", True) else None,
        entry["player"], tuple(entry.get("position", (0, i))), bool(entry.get("face_up", True)))
        for i, entry in enumerate(game.table_cards)) if game.enable_table else ()
    available = tuple(sorted(game.available_table_positions())) if game.enable_table else ()
    return PlayerTableView(viewer, game.enable_table, game.allow_play_in_front_of_players,
                           tuple(player.name for player in game.players), cards, available)


@dataclass(frozen=True)
class PersonalPileView:
    owner: int
    owner_name: str
    pile_index: int
    access: str
    ordered: bool
    order_by: str
    new_card: str
    size_order: str
    cards: tuple[str, ...]
    accessible: bool
    play: ActionAvailability
    take: ActionAvailability


@dataclass(frozen=True)
class PlayerPersonalPilesView:
    viewer: int
    enabled: bool
    piles: tuple[PersonalPileView, ...]


def build_player_personal_piles_view(game, viewer, hand_index=None):
    """Expose public pile cards in model order (top last), separately from access.

    Play availability refers to the supplied zero-based hand selection. Actions
    are available only for the current player; access itself is viewer-specific.
    """
    _validate_viewer(game, viewer)
    enabled = game.enable_table and game.enable_personal_piles
    piles = []
    if enabled:
        for owner, group in enumerate(game.personal_piles):
            for index, cards in enumerate(group):
                rule = game.personal_pile_settings[owner][index]
                context = ActionContext(hand_index=hand_index, owner=owner, pile_index=index)
                def available(action):
                    if viewer != game.current_player_index:
                        return ActionAvailability(False, "It is not this player's turn.")
                    return action_availability(game, action, context)
                piles.append(PersonalPileView(
                    owner, game.players[owner].name, index, rule["access"], rule["ordered"],
                    rule["order_by"], rule["new_card"], rule["size_order"], tuple(cards),
                    game.can_access_personal_pile(owner, index, viewer=viewer),
                    available("play_personal_pile"), available("take_personal_pile")))
    return PlayerPersonalPilesView(viewer, enabled, tuple(piles))


@dataclass(frozen=True)
class DiscardCardView:
    index: int
    card: str


@dataclass(frozen=True)
class DiscardPileView:
    source_index: int
    name: str
    card_count: int
    cards: tuple[DiscardCardView, ...]


@dataclass(frozen=True)
class PlayerDiscardView:
    viewer: int
    enabled: bool
    mode: str
    piles: tuple[DiscardPileView, ...]


def build_player_discard_view(game, viewer):
    """Prepare discard browsing without live lists or draw-deck order.

    Source indices include empty piles and match the session draw command.
    Cards are top first; top mode never copies deeper card identities.
    """
    _validate_viewer(game, viewer)
    piles = []
    if game.enable_discard_pile:
        sources = [(f"Shared discard {i + 1}", pile) for i, pile in enumerate(game.discard_piles)]
        for owner, group in enumerate(game.personal_discard_piles):
            sources.extend((f"{game.players[owner].name}'s discard {i + 1}", pile)
                           for i, pile in enumerate(group))
        for source, (name, pile) in enumerate(sources):
            indices = range(len(pile) - 1, -1, -1) if game.draw_from_discard_mode == "any" else ([len(pile) - 1] if pile else [])
            piles.append(DiscardPileView(source, name, len(pile),
                                         tuple(DiscardCardView(i, pile[i]) for i in indices)))
    return PlayerDiscardView(viewer, game.enable_discard_pile, game.draw_from_discard_mode, tuple(piles))
