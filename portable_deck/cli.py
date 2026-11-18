"""Small development hotseat client: python -m portable_deck.cli."""
import argparse
import json
import shlex
import sys
from dataclasses import asdict
from pathlib import Path

from .core.game import Game
from .core.playersessionview import build_player_session_view
from .core.turnstart import build_turn_start_view


HELP = "Commands: show, draw, play CARD, end, undo, pending, approve, reject, point, bet AMOUNT, pot PLAYER, help, quit. Card/player numbers start at 1."


class CLIClient:
    def __init__(self, game, output):
        self.game = game
        self.session = game.session
        self.output = output

    def write(self, text):
        print(text, file=self.output)

    def turn_work(self):
        work = build_turn_start_view(self.game)
        for notice in work.notifications:
            self.write(f"{notice.title}: {notice.message}")
        result = self.session.acknowledge_score_notifications(work.notifications) if work.active else None
        if result and result.checkpoint_error:
            self.write(f"Checkpoint failed: {result.checkpoint_error}")
        prompt = work.next_confirmation
        if prompt:
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
                self.write(json.dumps(asdict(build_player_session_view(self.game, viewer)), indent=2, ensure_ascii=False))
                return True
            if command == "pending":
                self.turn_work()
                return True
            if command == "undo":
                self.write("Undone." if self.session.undo() else "Nothing to undo.")
                self.turn_work()
                return True
            parameters = {}
            actions = {"draw": "draw_card", "play": "play_card", "end": "end_turn",
                       "point": "request_point", "bet": "play_chips", "pot": "take_pot"}
            if command in {"approve", "reject"}:
                prompt = build_turn_start_view(self.game).next_confirmation
                if prompt is None:
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
            if result.success:
                for message in result.messages:
                    self.write(message)
                if not result.messages:
                    self.write(result.message)
                self.turn_work()
            else:
                self.write(f"Unavailable: {result.message}")
            if result.checkpoint_error:
                self.write(f"Checkpoint failed: {result.checkpoint_error}")
        except ValueError as error:
            self.write(f"Error: {error}")
        return True


def run_cli(game, source, output):
    client = CLIClient(game, output)
    client.write(HELP)
    client.turn_work()
    for line in source:
        if not client.command(line):
            break
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Development hotseat client; no automatic saves.")
    parser.add_argument("--load", help="Load a session without modifying its save file")
    parser.add_argument("--deck", default=str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"))
    parser.add_argument("--players", type=int, default=2)
    parser.add_argument("--hand", type=int, default=3)
    parser.add_argument("--confirmations", action="store_true", help="Enable score/chip accounts and approval requests")
    args = parser.parse_args(argv)
    try:
        if args.load:
            game = Game.load_session(args.load)
        else:
            game = Game(args.players, args.deck, enable_undo=True,
                        score_enabled=args.confirmations, enable_chip_accounts=args.confirmations,
                        require_point_confirmation=args.confirmations,
                        require_pot_withdrawal_confirmation=args.confirmations)
            game.start(args.hand)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    try:
        return run_cli(game, sys.stdin, sys.stdout)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
