"""Immutable input data for chip controls, with no live Player references."""
from dataclasses import dataclass
from .actionavailability import ActionAvailability, action_availability
from .sessionstatus import ChipAccountStatus, build_session_status


@dataclass(frozen=True)
class ChipPlayerOption:
    index: int
    name: str
    account: str | None
    balance: int | None


@dataclass(frozen=True)
class ChipOptions:
    enabled: bool
    current_player: int
    players: tuple[ChipPlayerOption, ...]
    accounts: tuple[ChipAccountStatus, ...]
    minimum_bet: int | None
    maximum_bet: int | None
    default_purchase_amount: int
    pot: int | None
    buy_chips: ActionAvailability
    play_chips: ActionAvailability
    take_pot: ActionAvailability


def build_chip_options(game):
    """Describe current input ranges; execution still validates current state."""
    status = build_session_status(game)
    players = tuple(ChipPlayerOption(p.index, p.name, p.chip_account, p.chips) for p in status.players)
    current = game.current_player_index
    return ChipOptions(status.minimum_bet is not None, current, players, status.chip_accounts,
                       status.minimum_bet, players[current].balance,
                       max(1, status.minimum_bet or 1), status.chip_pot,
                       action_availability(game, "buy_chips"),
                       action_availability(game, "play_chips"),
                       action_availability(game, "take_pot"))
