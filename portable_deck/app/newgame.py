"""Create a started session from settings without any interface dependencies."""
from ..core.settingsvalidation import validate_settings_and_game
from .configurationinfo import configuration_info


def create_game(values):
    """Validate, prepare metadata and deal once; never persist or modify inputs."""
    settings, game = validate_settings_and_game(values)
    game.configuration_info = configuration_info(settings)
    game.start(settings["cards_per_player"])
    return game
