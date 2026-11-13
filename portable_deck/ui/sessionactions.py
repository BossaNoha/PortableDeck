"""Adapt shared execution results to existing presentation helpers."""

def execute_value(game, action, **parameters):
    result = game.session.execute(action, **parameters)
    if action in {"request_point", "reduce_score", "play_chips", "take_pot", "leave_session", "confirm_point", "confirm_pot", "return_player"}:
        return result.success, result.message
    return result.value if result.success else None
