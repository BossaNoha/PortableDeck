"""Create a started session from settings without any interface dependencies."""
from ..core.settingsvalidation import validate_settings_and_game
from .configurationinfo import configuration_info
from ..core.gamecreation import start_prepared_game


def create_game(values):
    """Validate, prepare metadata and deal once; never persist or modify inputs."""
    settings, game = validate_settings_and_game(values)
    return start_prepared_game(game, settings["cards_per_player"], configuration_info(settings))
