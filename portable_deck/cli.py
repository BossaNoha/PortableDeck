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
from .app.turnhandoff import TurnHandoffController
from .core.session import ActionResult
from .core.playersessionview import build_player_session_view
from .core.turnstart import build_turn_start_view
from .core.sharedoffer import shared_offer_view
from .core.drawpiles import DRAW_SOURCE_ACTIONS, draw_pile_options, resolve_draw_pile


HELP = "Commands: sources, source ID, offer, choose-offer CARD, discard-pile PLAYER PILE shared|personal DISCARD_PILE, take-pile PLAYER PILE, transfer-pile SOURCE_PLAYER SOURCE_PILE TARGET_PLAYER TARGET_PILE, show, draw, draw-many COUNT, deal COUNT, shuffle, play CARD, play-many CARD CARD [...], discard-many shared|personal PILE CARD CARD [...], discard-table-many shared|personal PILE CARD CARD [...], give-many PLAYER CARD CARD [...], take-many CARD CARD [...], end [PLAYER], skip, reverse, confirm-skip, ready, cancel, undo, pending, approve, reject, point, bet AMOUNT, pot PLAYER, help, quit. Card/player numbers start at 1."


class CLIClient:
    def __init__(self, game, output, structured=False, confirm_next_turn=False, confirm_skip=False):
        self.game = game
        self.session = game.session
        self.draw_pile_id = "main"
        self.output = output
        self.structured = structured
        self.turn_flow = TurnHandoffController(self.session, enabled=confirm_next_turn, confirm_skip=confirm_skip)

    def emit(self, kind, **values):
        print(json.dumps({"type": kind, **values}, ensure_ascii=False), file=self.output)

    def write(self, text):
        if self.structured:
            self.emit("message", message=text)
        else:
            print(text, file=self.output)

    def sync_draw_source(self):
        if not any(pile.id == self.draw_pile_id for pile in draw_pile_options(self.game)):
            self.draw_pile_id = "main"

    def turn_work(self):
        self.sync_draw_source()
        if self.turn_flow.pending:
            return
        if self.game.pending_shared_offer is not None:
            self.show_shared_offer()
            return
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

    def show_shared_offer(self):
        view = shared_offer_view(self.game)
        if self.structured:
            self.emit("shared_offer", offer=asdict(view))
        elif view.active:
            self.write(f"Shared offer — {view.player_name} chooses:")
            for index, card in enumerate(view.cards, 1):
                self.write(f"{index}. {card}")
            self.write("Use choose-offer CARD.")
        else:
            self.write("No shared offer is pending.")

    def report_result(self, action, result):
        # Internal values/events may contain private cards: never print them.
        if self.structured:
            self.emit("result", action=action, success=result.success, changed=result.changed,
                      code=result.code, message=result.message, messages=result.messages,
                      checkpoint_error=result.checkpoint_error)
        elif result.success:
            for message in result.messages or (result.message,):
                self.write(message)
        else:
            self.write(f"Unavailable: {result.message}")
        if result.success and result.code not in {"handoff_required", "handoff_cancelled", "skip_confirmation_required", "skip_cancelled"}:
            self.turn_work()
        if result.checkpoint_error and not self.structured:
            self.write(f"Checkpoint failed: {result.checkpoint_error}")

    def command(self, line):
        """Return False only for quit; command errors keep the client running."""
        try:
            parts = shlex.split(line)
            if not parts:
                return True
            command, args = parts[0].lower(), parts[1:]
            arity = {"sources": 0, "source": 1, "offer": 0, "choose-offer": 1, "deal": 1, "discard-pile": 4, "take-pile": 2, "transfer-pile": 4, "draw-many": 1, "shuffle": 0, "confirm-skip": 0, "skip": 0, "reverse": 0, "show": 0, "draw": 0, "play": 1, "end": 0, "undo": 0,
                     "pending": 0, "approve": 0, "reject": 0, "point": 0,
                     "bet": 1, "pot": 1, "help": 0, "quit": 0, "ready": 0, "cancel": 0}
            if command == "give-many":
                if len(args) < 3:
                    raise ValueError("Use give-many PLAYER CARD CARD [...].")
            elif command in {"discard-many", "discard-table-many"}:
                if len(args) < 4 or args[0] not in {"shared", "personal"}:
                    raise ValueError(f"Use {command} shared|personal PILE CARD CARD [...].")
            elif command in {"play-many", "take-many"}:
                if len(args) < 2:
                    raise ValueError(f"Use {command} with at least two card numbers.")
            elif command not in arity or (len(args) != arity[command] and not (command == "end" and len(args) == 1)):
                raise ValueError("Unknown command or incorrect arguments. Use help.")
            if command == "quit":
                return False
            if command == "help":
                self.write(HELP)
                return True
            if self.game.pending_shared_offer is not None and command not in {"show", "offer", "choose-offer", "undo"}:
                self.report_result(command, ActionResult(False, message="Finish the shared offer first.", code="shared_offer_pending"))
                return True
            if self.game.pending_shared_offer is not None and command in {"show", "offer"}:
                self.show_shared_offer()
                return True
            if command in {"ready", "cancel", "confirm-skip"}:
                result = (self.turn_flow.confirm_skip() if command == "confirm-skip" else
                          self.turn_flow.confirm() if command == "ready" else self.turn_flow.cancel())
                self.report_result("end_turn" if command != "cancel" else "cancel_handoff", result)
                return True
            if self.turn_flow.pending:
                self.report_result(command, ActionResult(False, code="handoff_pending",
                    message="Use confirm-skip or cancel first." if self.turn_flow.awaiting_skip else
                            "Confirm with ready or cancel the pending handoff first."))
                return True
            self.sync_draw_source()
            if command == "sources":
                options = draw_pile_options(self.game)
                if self.structured:
                    self.emit("draw_sources", selected=self.draw_pile_id, piles=[asdict(pile) for pile in options])
                else:
                    for pile in options:
                        self.write(f"{pile.id}: {pile.name} ({pile.card_count} cards)" + (" [selected]" if pile.id == self.draw_pile_id else ""))
                return True
            if command == "source":
                resolve_draw_pile(self.game, args[0])
                self.draw_pile_id = args[0]
                self.write(f"Draw source: {self.draw_pile_id}")
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
                result = self.session.undo_result()
                if self.structured:
                    self.emit("result", action="undo", success=result.success, changed=result.changed,
                              code=result.code, message=result.message, checkpoint_error=result.checkpoint_error)
                else:
                    self.write(result.message)
                    if result.checkpoint_error:
                        self.write(f"Checkpoint failed: {result.checkpoint_error}")
                self.turn_work()
                return True
            parameters = {}
            actions = {"offer": "start_shared_offer", "choose-offer": "choose_shared_offer", "deal": "deal_cards", "discard-pile": "discard_whole_personal_pile", "take-pile": "take_whole_personal_pile", "transfer-pile": "transfer_personal_pile", "draw-many": "draw_cards", "shuffle": "shuffle_draw_deck", "discard-table-many": "discard_table_cards", "take-many": "take_table_cards", "give-many": "give_cards", "discard-many": "discard_cards", "play-many": "play_cards", "skip": "end_turn", "reverse": "reverse_turn_order", "draw": "draw_card", "play": "play_card", "end": "end_turn",
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
                if command == "discard-pile":
                    if args[2] not in {"shared", "personal"}:
                        raise ValueError("Use discard-pile PLAYER PILE shared|personal DISCARD_PILE.")
                    parameters = {"owner": self.positive(args[0]) - 1, "pile_index": self.positive(args[1]) - 1,
                                  "personal": args[2] == "personal", "discard_pile_index": self.positive(args[3]) - 1}
                elif command == "take-pile":
                    parameters = {"owner": self.positive(args[0]) - 1, "pile_index": self.positive(args[1]) - 1}
                elif command == "transfer-pile":
                    parameters = dict(zip(("source_owner", "source_pile", "target_owner", "target_pile"),
                                          [self.positive(arg) - 1 for arg in args]))
                elif command == "choose-offer":
                    parameters["card_index"] = self.positive(args[0]) - 1
                elif command in {"draw-many", "deal"}:
                    parameters["count"] = self.positive(args[0])
                elif command == "give-many":
                    parameters = {"target": self.positive(args[0]) - 1,
                                  "card_indices": [self.positive(arg) - 1 for arg in args[1:]]}
                elif command in {"discard-many", "discard-table-many"}:
                    parameters = {"personal": args[0] == "personal", "pile_index": self.positive(args[1]) - 1,
                                  "card_indices": [self.positive(arg) - 1 for arg in args[2:]]}
                elif command in {"play-many", "take-many"}:
                    parameters["card_indices"] = [self.positive(arg) - 1 for arg in args]
                elif command == "skip":
                    parameters["skip_next"] = True
                elif command == "play":
                    parameters["card_index"] = self.positive(args[0]) - 1
                elif command == "bet":
                    parameters["amount"] = self.positive(args[0])
                elif command == "pot":
                    parameters["player_index"] = self.positive(args[0]) - 1
                elif command == "end" and args:
                    parameters["next_player"] = self.positive(args[0]) - 1
            if action in DRAW_SOURCE_ACTIONS and self.draw_pile_id != "main":
                parameters["draw_pile_id"] = self.draw_pile_id
            if action == "end_turn":
                result = self.turn_flow.request(lambda: self.session.execute(action, **parameters),
                                                next_player=parameters.get("next_player"),
                                                skip_next=parameters.get("skip_next", False))
            else:
                result = self.session.execute(action, **parameters)
            self.report_result(action, result)
        except ValueError as error:
            if self.structured:
                self.emit("error", code="invalid_command", message=str(error))
            else:
                self.write(f"Error: {error}")
        return True


def run_cli(game, source, output, structured=False, confirm_next_turn=False, confirm_skip=False):
    client = CLIClient(game, output, structured=structured, confirm_next_turn=confirm_next_turn, confirm_skip=confirm_skip)
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
    parser.add_argument("--confirm-next-turn", action="store_true", help="Require ready after end before advancing the turn")
    parser.add_argument("--choose-next-player", action="store_true", help="Allow end PLAYER for new games")
    parser.add_argument("--reverse-turn-order", action="store_true", help="Allow reverse for new games")
    parser.add_argument("--skip-next-player", action="store_true", help="Allow skip for new games")
    parser.add_argument("--confirm-skip", action="store_true", help="Require confirm-skip before skipping a player")
    parser.add_argument("--play-multiple-cards", action="store_true", help="Allow play-many for new games")
    parser.add_argument("--discard-multiple-cards", action="store_true", help="Allow discard-many for new games")
    parser.add_argument("--give-multiple-cards", action="store_true", help="Allow give-many for new games")
    parser.add_argument("--take-multiple-cards", action="store_true", help="Allow take-many for new games")
    parser.add_argument("--discard-multiple-table-cards", action="store_true", help="Allow discard-table-many for new games")
    parser.add_argument("--shuffle-draw-deck", action="store_true", help="Allow shuffle for new games")
    parser.add_argument("--draw-multiple-cards", action="store_true", help="Allow draw-many for new games")
    parser.add_argument("--transfer-personal-piles", action="store_true", help="Enable whole-pile transfers with two owner-only piles per player for new games")
    parser.add_argument("--take-whole-personal-pile", action="store_true", help="Enable take-pile and personal piles for new games")
    parser.add_argument("--discard-whole-personal-pile", action="store_true", help="Enable discard-pile and personal piles for new games")
    parser.add_argument("--deal-cards", action="store_true", help="Allow deal COUNT for new games")
    parser.add_argument("--shared-offer", action="store_true", help="Enable offer and choose-offer for new games")
    parser.add_argument("--draw-pile", nargs=4, action="append", default=[],
                        metavar=("ID", "NAME", "OWNER", "COUNT"),
                        help="Split remaining cards into a pile; OWNER is shared or a player number. Repeat for more piles.")
    args = parser.parse_args(argv)
    try:
        if args.load:
            game = load_session(Game, args.load)
        else:
            game = create_game({
                "num_players": args.players,
                "enable_draw_pile_setup": bool(args.draw_pile),
                "draw_pile_setup": [{"id": pile_id, "name": name,
                                     "owner": None if owner == "shared" else CLIClient.positive(owner) - 1,
                                     "count": int(count)} for pile_id, name, owner, count in args.draw_pile],
                "cards_per_player": args.hand,
                # CLI-relative paths keep their existing working-directory meaning.
                "deck_path": str(Path(args.deck).absolute()),
                "enable_undo": True,
                "allow_choose_next_player": args.choose_next_player,
                "allow_reverse_turn_order": args.reverse_turn_order,
                "allow_skip_next_player": args.skip_next_player,
                "allow_play_multiple_cards": args.play_multiple_cards,
                "allow_discard_multiple_cards": args.discard_multiple_cards,
                "allow_discard_multiple_table_cards": args.discard_multiple_table_cards,
                "allow_move_table_card_to_discard": args.discard_multiple_table_cards,
                "allow_take_multiple_cards": args.take_multiple_cards,
                "allow_take_from_table": args.take_multiple_cards,
                "allow_transfer_personal_piles": args.transfer_personal_piles,
                "enable_personal_piles": args.transfer_personal_piles or args.take_whole_personal_pile or args.discard_whole_personal_pile,
                "allow_discard_whole_personal_pile": args.discard_whole_personal_pile,
                "allow_take_whole_personal_pile": args.take_whole_personal_pile,
                "personal_pile_count": 2 if args.transfer_personal_piles else 1,
                "enable_special_actions": args.shuffle_draw_deck or args.draw_multiple_cards or args.deal_cards or args.shared_offer,
                "allow_shared_offer": args.shared_offer,
                "allow_deal_cards": args.deal_cards,
                "allow_draw_multiple_cards": args.draw_multiple_cards,
                "allow_shuffle_draw_deck": args.shuffle_draw_deck,
                "enable_interactions": args.give_multiple_cards,
                "interaction_options": {"give_cards": args.give_multiple_cards},
                "enable_score_counter": args.confirmations,
                "enable_chip_accounts": args.confirmations,
                "require_point_confirmation": args.confirmations,
                "require_pot_withdrawal_confirmation": args.confirmations,
            })
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    try:
        return run_cli(game, sys.stdin, sys.stdout, structured=args.json, confirm_next_turn=args.confirm_next_turn, confirm_skip=args.confirm_skip)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
