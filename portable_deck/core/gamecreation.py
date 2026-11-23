"""Shared construction/start operations for new and restarted sessions."""
import copy
import inspect


def create_configured_game(parameters):
    from .game import Game
    return Game(**copy.deepcopy(parameters))


def start_prepared_game(game, cards_per_player, configuration_info):
    game.configuration_info = copy.deepcopy(configuration_info)
    game.start(cards_per_player)
    return game


def restart_game(game, keep_scores=False):
    """Recreate current rules, independently of app settings or any interface."""
    from .game import Game
    aliases = {"num_players": len(game.players), "deck_path": game.deck,
               "player_names": [player.name for player in game.players]}
    parameters = {name: aliases[name] if name in aliases else getattr(game, name)
                  for name in inspect.signature(Game).parameters}
    restarted = create_configured_game(parameters)
    if not game.reset_chip_accounts_on_restart:
        restarted.chip_balances = game.chip_balances.copy()
        restarted.chip_pot = game.chip_pot
    start_prepared_game(restarted, game.cards_per_player, game.configuration_info)
    # Configured piles were freshly populated by start; retain other runtime
    # pile identities as empty until they have their own initial setup rules.
    piles = restarted.draw_piles.snapshot()
    known = {pile["id"] for pile in piles}
    for pile in game.draw_piles.snapshot():
        if pile["id"] == "main":
            piles[0] = pile
        elif pile["id"] not in known:
            piles.append({**pile, "cards": []})
    restarted.draw_piles.restore(piles)
    if keep_scores:
        restarted.scores = game.scores.copy()
        restarted.team_scores = game.team_scores.copy()
    return restarted
