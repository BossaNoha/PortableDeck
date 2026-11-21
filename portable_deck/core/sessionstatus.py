"""Immutable, read-only session status for graphical and text clients."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PlayerStatus:
    index: int
    name: str
    card_count: int
    active: bool
    is_current: bool
    dealer: bool
    team_id: str | None
    team_name: str | None
    score: int | None
    score_owner: str | None
    team_score: int | None
    chips: int | None
    chip_account: str | None


@dataclass(frozen=True)
class ChipAccountStatus:
    id: str
    owner_name: str
    members: tuple[int, ...]
    balance: int
    shared: bool


@dataclass(frozen=True)
class TeamStatus:
    id: str
    name: str
    members: tuple[int, ...]
    dealer: bool
    score: int | None


@dataclass(frozen=True)
class PileStatus:
    id: str
    name: str
    card_count: int
    owner: int | None = None


@dataclass(frozen=True)
class SessionStatus:
    players: tuple[PlayerStatus, ...]
    teams: tuple[TeamStatus, ...]
    chip_accounts: tuple[ChipAccountStatus, ...]
    draw_count: int
    discard_piles: tuple[PileStatus, ...] | None
    table_count: int | None
    chip_pot: int | None
    minimum_bet: int | None
    turn_direction: int | None = None


def build_session_status(game):
    """Prepare actual values without display rules, card identities or mutation.

    None represents a disabled resource. Shared account IDs let clients group
    balances without accidentally adding the same team's chips more than once.
    """
    g = game
    active = set(g.active_player_indices())
    players = []
    account_members = {}
    for i, player in enumerate(g.players):
        team_name = g.player_team_name(i)
        team_id = g.player_teams[i] if team_name is not None else None
        account = None
        if g.enable_chip_accounts:
            account = f"team:{team_id}" if g.share_team_chips and team_id else f"player:{i}"
            account_members.setdefault(account, []).append(i)
        score_owner = None
        if g.score_enabled:
            score_owner = f"team:{team_id}" if g.share_team_score and team_id else f"player:{i}"
        players.append(PlayerStatus(
            i, player.name, len(player.hand), i in active,
            i in active and i == g.current_player_index, g.player_is_dealer(i),
            team_id, team_name, g.scores[i] if g.score_enabled else None, score_owner,
            g.team_scores[team_id] if g.enable_team_score and team_id else None,
            g.chip_balance(i) if g.enable_chip_accounts else None, account))
    accounts = []
    for identity, members in account_members.items():
        first = players[members[0]]
        shared = identity.startswith("team:")
        accounts.append(ChipAccountStatus(identity, first.team_name if shared else first.name,
                                           tuple(members), first.chips, shared))
    teams = []
    if g.enable_roles_teams:
        for team in g.teams:
            dealer = team["id"] == "dealer"
            members = tuple(i for i in range(len(g.players)) if
                (g.player_is_dealer(i) if dealer else g.player_teams[i] == team["id"]))
            teams.append(TeamStatus(team["id"], team["name"], members, dealer,
                                   g.team_scores[team["id"]] if g.enable_team_score and not dealer else None))
    discard = None
    if g.enable_discard_pile:
        discard = [PileStatus(f"shared:{i}", f"Shared discard {i + 1}", len(pile))
                   for i, pile in enumerate(g.discard_piles)]
        for owner, piles in enumerate(g.personal_discard_piles):
            discard.extend(PileStatus(f"personal:{owner}:{i}", f"{g.players[owner].name}'s discard {i + 1}", len(pile), owner)
                           for i, pile in enumerate(piles))
        discard = tuple(discard)
    personal_count = (sum(len(pile) for group in g.personal_piles for pile in group)
                      if g.enable_personal_piles else 0)
    return SessionStatus(tuple(players), tuple(teams), tuple(accounts), len(g.deck.flat_deck),
        discard, len(g.table_cards) + personal_count if g.enable_table else None,
        g.chip_pot if g.enable_chip_accounts else None,
        g.minimum_bet if g.enable_chip_accounts else None,
        g.turn_direction if g.allow_reverse_turn_order else None)
