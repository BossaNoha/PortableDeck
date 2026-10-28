#game.py
from deck import Deck
from player import Player
import json

class Game:
    def __init__(
        self,
        num_players,
        deck_path,
        player_names=None,
        score_enabled=False,
        require_point_confirmation=False,
        allow_take_from_table=False,
        allow_move_table_card_to_discard=False,
        allow_manual_table_cleanup=False,
        clear_table_on_round_end=False,
    ):
        if not isinstance(num_players, int) or isinstance(num_players, bool) or num_players < 1:
            raise ValueError("num_players must be a positive integer")
        if player_names is not None and len(player_names) != num_players:
            raise ValueError("player_names must contain one name for each player")
        self.players = [
            Player(player_names[i] if player_names is not None else f"Player{i+1}")
            for i in range(num_players)
        ]
        self.deck = Deck(deck_path)
        self.discard_pile = []
        self.table_cards = []
        self.current_player_index = 0
        self.history = []
        self.cards_drawn_this_turn = 0
        self.cards_per_player = 0
        self.score_enabled = score_enabled
        self.require_point_confirmation = require_point_confirmation and score_enabled
        self.scores = [0 for _ in self.players]
        self.pending_point_request = None
        self.allow_take_from_table = allow_take_from_table
        self.allow_move_table_card_to_discard = allow_move_table_card_to_discard
        self.allow_manual_table_cleanup = allow_manual_table_cleanup
        self.clear_table_on_round_end = clear_table_on_round_end

    def request_point(self):
        if not self.score_enabled:
            return False, "Point scoring is disabled."
        if self.pending_point_request is not None:
            return False, "A point request is already waiting for a decision."

        requester = self.current_player_index
        if not self.require_point_confirmation:
            player_name = self.players[requester].name
            self.scores[requester] += 1
            self.log_action(player_name, "point_awarded")
            return True, f"{player_name} received a point."

        other_players = [index for index in range(len(self.players)) if index != requester]
        if not other_players:
            player_name = self.players[requester].name
            self.scores[requester] += 1
            self.log_action(player_name, "point_awarded")
            return True, f"{player_name} received a point (no other players to confirm)."

        self.pending_point_request = {"requester": requester, "confirmed_by": []}
        self.log_action(self.players[requester].name, "point_requested")
        return True, f"{self.players[requester].name} requested a point."

    def current_player_must_confirm_point(self):
        request = self.pending_point_request
        if request is None or self.current_player_index == request["requester"]:
            return False
        return self.current_player_index not in request["confirmed_by"]

    def confirm_point_request(self, approved):
        if not self.current_player_must_confirm_point():
            return False, "There is no point request awaiting your confirmation."

        request = self.pending_point_request
        voter_name = self.players[self.current_player_index].name
        requester_name = self.players[request["requester"]].name
        if not approved:
            self.log_action(voter_name, "point_denied")
            self.pending_point_request = None
            return True, f"{voter_name} denied the request. No point was awarded."

        request["confirmed_by"].append(self.current_player_index)
        self.log_action(voter_name, "point_confirmed")
        other_players = [index for index in range(len(self.players)) if index != request["requester"]]
        if all(index in request["confirmed_by"] for index in other_players):
            self.scores[request["requester"]] += 1
            self.log_action(requester_name, "point_awarded")
            self.pending_point_request = None
            return True, f"All players approved. {requester_name} received a point."
        return True, f"{voter_name} approved the request. The remaining players will be asked on their turns."

    def start(self, cards_per_player=5):
        if not isinstance(cards_per_player, int) or isinstance(cards_per_player, bool) or cards_per_player < 0:
            raise ValueError("cards_per_player must be a non-negative integer")

        required_cards = len(self.players) * cards_per_player
        available_cards = len(self.deck.flat_deck)
        if required_cards > available_cards:
            raise ValueError(
                f"Cannot deal {cards_per_player} cards to {len(self.players)} players: "
                f"the deck has {available_cards} cards, but {required_cards} are required."
            )

        self.cards_per_player = cards_per_player
        self.deck.shuffle()
        print("Deck shuffled. Starting the game...")
        for _ in range(cards_per_player):
            for player in self.players:
                player.draw_card(self.deck.draw_card())

    def restart(self, keep_scores=False):
        """Create a fresh game with the same setup, optionally retaining scores."""
        restarted = Game(
            num_players=len(self.players),
            deck_path=self.deck.path,
            player_names=[player.name for player in self.players],
            score_enabled=self.score_enabled,
            require_point_confirmation=self.require_point_confirmation,
            allow_take_from_table=self.allow_take_from_table,
            allow_move_table_card_to_discard=self.allow_move_table_card_to_discard,
            allow_manual_table_cleanup=self.allow_manual_table_cleanup,
            clear_table_on_round_end=self.clear_table_on_round_end,
        )
        restarted.start(self.cards_per_player)
        if keep_scores:
            restarted.scores = self.scores.copy()
        return restarted

    def log_draws_for_turn(self):
        if self.cards_drawn_this_turn > 0:
            player_name = self.players[self.current_player_index].name
            entry = {"player": player_name, "action": "draw_multiple", "count": self.cards_drawn_this_turn}
            self.history.append(entry)
            self.cards_drawn_this_turn = 0

    def deal_card_to_current(self):
        card = self.deck.draw_card()
        player = self.players[self.current_player_index]
        if card:
            player.draw_card(card)
            self.cards_drawn_this_turn += 1
        return card

    def discard_from_current(self, index):
        player = self.players[self.current_player_index]
        card = player.play_card(index)

        if card:
            self.discard_pile.append(card)
            self.log_action(player.name, "discard", card)
            return card   # ✅ success
        else:
            return None   # ❌ failure

    def play_to_table(self, index):
        player = self.players[self.current_player_index]
        card = player.play_card(index)
        if card:
            self.table_cards.append({"player": player.name, "card": card})
            self.log_action(player.name, "play", card)
            return card
        return None

    def take_from_table(self, index):
        if not self.allow_take_from_table or not 0 <= index < len(self.table_cards):
            return None
        entry = self.table_cards.pop(index)
        card = entry["card"]
        player = self.players[self.current_player_index]
        player.draw_card(card)
        self.log_action(player.name, "take_from_table", card)
        return card

    def move_table_card_to_discard(self, index):
        if (
            not self.allow_move_table_card_to_discard
            or not 0 <= index < len(self.table_cards)
        ):
            return None
        entry = self.table_cards.pop(index)
        card = entry["card"]
        self.discard_pile.append(card)
        self.log_action(self.players[self.current_player_index].name, "table_to_discard", card)
        return card

    def clear_table(self, automatic=False):
        if automatic:
            if not self.clear_table_on_round_end:
                return 0
        elif not self.allow_manual_table_cleanup:
            return 0
        count = len(self.table_cards)
        if count:
            self.discard_pile.extend(entry["card"] for entry in self.table_cards)
            self.table_cards.clear()
            self.history.append({
                "player": self.players[self.current_player_index].name,
                "action": "clear_table",
                "count": count,
            })
        return count

    def finish_turn(self):
        """End a turn and report whether it ended the round and cleared the table."""
        self.log_draws_for_turn()
        round_ended = self.current_player_index == len(self.players) - 1
        cleared_count = 0
        if round_ended and self.clear_table_on_round_end:
            cleared_count = self.clear_table(automatic=True)
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        return round_ended, cleared_count

    def log_action(self, player_name, action, card=None):
        entry = {"player": player_name, "action": action}
        if card:
            entry["card"] = card
        self.history.append(entry)

    def next_turn(self):
        confirm = input("End turn? (y/n): ").strip().lower()
        if confirm == "y":
            round_ended, cleared_count = self.finish_turn()
            print("Turn ended.")
            if round_ended:
                print("The round has ended.")
            if cleared_count:
                print(f"The table was cleared; {cleared_count} card(s) moved to the discard pile.")
        else:
            print("Continuing current turn.")

    def show_discard_pile(self):
        print("\nDiscard Pile:")
        if self.discard_pile:
            for card in self.discard_pile:
                print(f"- {card}")
        else:
            print("Discard pile is empty.")

    def show_log_to_player(self, player_index):
        player_name = self.players[player_index].name
        print(f"\n--- Game Log for {player_name} ---")
        if not self.history:
            print("No actions recorded yet.")
            return
        for entry in self.history:
            actor = entry["player"]
            action = entry["action"]
            if action == "draw_multiple":
                count = entry["count"]
                if actor == player_name:
                    print(f"{actor} drew {count} card{'s' if count > 1 else ''}")
                else:
                    print(f"{actor} drew some cards")
            elif action == "discard":
                card = entry.get("card")
                if actor == player_name:
                    print(f"You discarded: {card}")
                else:
                    print(f"{actor} discarded a card: {card}")
            else:
                print(f"{actor} performed action: {action}")

    def save_discard_pile(self, path):
        with open(path, "w") as f:
            json.dump(self.discard_pile, f, indent=2)

    def save_session(self, path):
        """Save the complete state needed to continue this game later."""
        state = {
            "deck_path": self.deck.path,
            "remaining_deck": self.deck.flat_deck,
            "players": [{"name": player.name, "hand": player.hand} for player in self.players],
            "discard_pile": self.discard_pile,
            "table_cards": self.table_cards,
            "current_player_index": self.current_player_index,
            "history": self.history,
            "cards_drawn_this_turn": self.cards_drawn_this_turn,
            "cards_per_player": self.cards_per_player,
            "score_enabled": self.score_enabled,
            "require_point_confirmation": self.require_point_confirmation,
            "scores": self.scores,
            "pending_point_request": self.pending_point_request,
            "allow_take_from_table": self.allow_take_from_table,
            "allow_move_table_card_to_discard": self.allow_move_table_card_to_discard,
            "allow_manual_table_cleanup": self.allow_manual_table_cleanup,
            "clear_table_on_round_end": self.clear_table_on_round_end,
        }
        with open(path, "w", encoding="utf-8") as session_file:
            json.dump(state, session_file, indent=2)

    @classmethod
    def load_session(cls, path):
        with open(path, "r", encoding="utf-8") as session_file:
            state = json.load(session_file)

        game = cls.__new__(cls)
        game.deck = Deck(state["deck_path"])
        game.deck.flat_deck = state["remaining_deck"]
        game.players = []
        for saved_player in state["players"]:
            player = Player(saved_player["name"])
            player.hand = saved_player["hand"]
            game.players.append(player)
        if not game.players:
            raise ValueError("Saved game has no players")
        game.discard_pile = state["discard_pile"]
        game.table_cards = state.get("table_cards", [])
        game.current_player_index = state["current_player_index"]
        if not 0 <= game.current_player_index < len(game.players):
            raise ValueError("Saved game has an invalid current player")
        game.history = state["history"]
        game.cards_drawn_this_turn = state["cards_drawn_this_turn"]
        game.cards_per_player = state.get("cards_per_player")
        game.score_enabled = state.get("score_enabled", False)
        game.require_point_confirmation = state.get("require_point_confirmation", False)
        game.scores = state.get("scores", [0 for _ in game.players])
        game.pending_point_request = state.get("pending_point_request")
        game.allow_take_from_table = state.get("allow_take_from_table", False)
        game.allow_move_table_card_to_discard = state.get("allow_move_table_card_to_discard", False)
        game.allow_manual_table_cleanup = state.get("allow_manual_table_cleanup", False)
        game.clear_table_on_round_end = state.get("clear_table_on_round_end", False)
        if game.cards_per_player is None:
            drawn = sum(
                entry.get("count", 0)
                for entry in game.history
                if entry.get("action") == "draw_multiple"
            ) + game.cards_drawn_this_turn
            cards_in_play = (
                sum(len(player.hand) for player in game.players)
                + len(game.discard_pile)
                + len(game.table_cards)
            )
            dealt_cards = cards_in_play - drawn
            game.cards_per_player = (
                dealt_cards // len(game.players)
                if dealt_cards >= 0 and dealt_cards % len(game.players) == 0
                else 0
            )
        return game
