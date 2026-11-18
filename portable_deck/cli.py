"""Small development hotseat client: python -m portable_deck.cli."""
import argparse
import json
import shlex
import sys
from dataclasses import asdict
from pathlib import Path

from .core.game import Game
from .app.newgame import create_game
from .app.sessionstorage import load_session
from .core.playersessionview import build_player_session_view
from .core.turnstart import build_turn_start_view


HELP = "Commands: show, draw, play CARD, end, undo, pending, approve, reject, point, bet AMOUNT, pot PLAYER, help, quit. Card/player numbers start at 1."


class CLIClient:
    def __init__(self, game, output, structured=False):
        self.game = game
        self.session = game.session
        self.output = output
        self.structured = structured

    def emit(self, kind, **values):
        print(json.dumps({"type": kind, **values}, ensure_ascii=False), file=self.output)

    def write(self, text):
        if self.structured:
            self.emit("message", message=text)
        else:
            print(text, file=self.output)

    def turn_work(self):
        work = build_turn_start_view(self.game)
        for notice in work.notifications:
            if self.structured:
                self.emit("notification", notice=asdict(notice))
            else:
                self.write(f"{notice.title}: {notice.message}")
        result = self.session.acknowledge_score_notifications(work.notifications) if work.active else None
        if result and result.checkpoint_error:
            if self.structured:
                self.emit("checkpoint_error", code="checkpoint_failed", message=result.checkpoint_error)
            else:
                self.write(f"Checkpoint failed: {result.checkpoint_error}")
        prompt = work.next_confirmation
        if prompt:
            if self.structured:
                self.emit("confirmation", action=prompt.action, notice=asdict(prompt.notice))
            else:
                self.write(f"{prompt.notice.title}: {prompt.notice.message}")
                self.write("Use approve or reject for this request.")

    @staticmethod
    def positive(value):
        number = int(value)
        if number < 1:
            raise ValueError("Use a positive whole number.")
        return number

    def command(self, line):
        """Return False only for quit; command errors keep the client running."""
        try:
            parts = shlex.split(line)
            if not parts:
                return True
            command, args = parts[0].lower(), parts[1:]
            arity = {"show": 0, "draw": 0, "play": 1, "end": 0, "undo": 0,
                     "pending": 0, "approve": 0, "reject": 0, "point": 0,
                     "bet": 1, "pot": 1, "help": 0, "quit": 0}
            if command not in arity or len(args) != arity[command]:
                raise ValueError("Unknown command or incorrect arguments. Use help.")
            if command == "quit":
                return False
            if command == "help":
                self.write(HELP)
                return True
            if command == "show":
                viewer = build_turn_start_view(self.game).player
                view = asdict(build_player_session_view(self.game, viewer))
                if self.structured:
                    self.emit("view", view=view)
                else:
                    self.write(json.dumps(view, indent=2, ensure_ascii=False))
                return True
            if command == "pending":
                self.turn_work()
                return True
            if command == "undo":
                success = self.session.undo()
                message = "Undone." if success else "Nothing to undo."
                if self.structured:
                    self.emit("result", action="undo", success=success, changed=success,
                              code="" if success else "nothing_to_undo", message=message,
                              checkpoint_error=self.session.last_checkpoint_error if success else None)
                else:
                    self.write(message)
                self.turn_work()
                return True
            parameters = {}
            actions = {"draw": "draw_card", "play": "play_card", "end": "end_turn",
                       "point": "request_point", "bet": "play_chips", "pot": "take_pot"}
            if command in {"approve", "reject"}:
                prompt = build_turn_start_view(self.game).next_confirmation
                if prompt is None:
                    if self.structured:
                        self.emit("result", action=command, success=False, changed=False,
                                  code="confirmation_not_required", message="No confirmation is required from this player.")
                        return True
                    raise ValueError("No confirmation is required from this player.")
                action, parameters = prompt.action, {"approved": command == "approve"}
            else:
                action = actions[command]
                if command == "play":
                    parameters["card_index"] = self.positive(args[0]) - 1
                elif command == "bet":
                    parameters["amount"] = self.positive(args[0])
                elif command == "pot":
                    parameters["player_index"] = self.positive(args[0]) - 1
            result = self.session.execute(action, **parameters)
            # Internal events/values may contain private cards: never print them.
            if self.structured:
                self.emit("result", action=action, success=result.success, changed=result.changed,
                          code=result.code, message=result.message, messages=result.messages,
                          checkpoint_error=result.checkpoint_error)
                if result.success:
                    self.turn_work()
            elif result.success:
                for message in result.messages:
                    self.write(message)
                if not result.messages:
                    self.write(result.message)
                self.turn_work()
            else:
                self.write(f"Unavailable: {result.message}")
            if result.checkpoint_error and not self.structured:
                self.write(f"Checkpoint failed: {result.checkpoint_error}")
        except ValueError as error:
            if self.structured:
                self.emit("error", code="invalid_command", message=str(error))
            else:
                self.write(f"Error: {error}")
        return True


def run_cli(game, source, output, structured=False):
    client = CLIClient(game, output, structured=structured)
    client.write(HELP)
    client.turn_work()
    for line in source:
        if not client.command(line):
            break
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Development hotseat client; no automatic saves.")
    parser.add_argument("--load", help="Load a session without modifying its save file")
    parser.add_argument("--json", action="store_true", help="Emit command-stream output as JSON Lines")
    parser.add_argument("--deck", default=str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"))
    parser.add_argument("--players", type=int, default=2)
    parser.add_argument("--hand", type=int, default=3)
    parser.add_argument("--confirmations", action="store_true", help="Enable score/chip accounts and approval requests")
    args = parser.parse_args(argv)
    try:
        if args.load:
            game = load_session(Game, args.load)
        else:
            game = create_game({
                "num_players": args.players,
                "cards_per_player": args.hand,
                # CLI-relative paths keep their existing working-directory meaning.
                "deck_path": str(Path(args.deck).absolute()),
                "enable_undo": True,
                "enable_score_counter": args.confirmations,
                "enable_chip_accounts": args.confirmations,
                "require_point_confirmation": args.confirmations,
                "require_pot_withdrawal_confirmation": args.confirmations,
            })
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    try:
        return run_cli(game, sys.stdin, sys.stdout, structured=args.json)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
