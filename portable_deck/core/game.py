#game.py
from .deck import Deck
from .player import Player
import json
from .gamechipactions import ChipBankActions
from .gametable import GameTableActions
from .gamescoring import GameScoringActions
from .gameundo import GameUndoActions

class Game(GameScoringActions, GameUndoActions, ChipBankActions, GameTableActions):
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
        allow_positioned_play=False,
        occupied_slot_action="invalid",
        enable_undo=False,
        allow_move_cards_on_table=False,
        allow_play_in_front_of_players=False,
        allow_draw_from_discard=False,
        draw_from_discard_mode="top",
        allow_face_down_table_cards=False,
        allow_move_table_sequences=False,
        allow_recycle_discard_to_deck=False,
        shared_discard_pile_count=1,
        personal_discard_pile_count=0,
        enable_chip_accounts=False,
        minimum_bet=1,
        starting_balance=100,
        require_pot_withdrawal_confirmation=False,
    ):
        if not isinstance(num_players, int) or isinstance(num_players, bool) or num_players < 1:
            raise ValueError("num_players must be a positive integer")
        if player_names is not None and len(player_names) != num_players:
            raise ValueError("player_names must contain one name for each player")
        if not isinstance(minimum_bet, int) or isinstance(minimum_bet, bool) or minimum_bet < 1:
            raise ValueError("minimum_bet must be a positive integer")
        if not isinstance(starting_balance, int) or isinstance(starting_balance, bool) or starting_balance < 0:
            raise ValueError("starting_balance must be a non-negative integer")
        for label, value in (("shared_discard_pile_count", shared_discard_pile_count), ("personal_discard_pile_count", personal_discard_pile_count)):
            if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 20:
                raise ValueError(f"{label} must be an integer between 0 and 20")
        if shared_discard_pile_count == 0 and personal_discard_pile_count == 0:
            shared_discard_pile_count = 1
        self.players = [
            Player(player_names[i] if player_names is not None else f"Player{i+1}")
            for i in range(num_players)
        ]
        self.deck = Deck(deck_path)
        self.shared_discard_pile_count = shared_discard_pile_count
        self.personal_discard_pile_count = personal_discard_pile_count
        self.discard_piles = [[] for _ in range(shared_discard_pile_count)]
        self.personal_discard_piles = [
            [[] for _ in range(personal_discard_pile_count)] for _ in self.players
        ]
        self.table_cards = []
        self.current_player_index = 0
        self.history = []
        self.gui_log = []
        self.enable_undo = bool(enable_undo)
        self.allow_move_cards_on_table = bool(allow_move_cards_on_table or allow_move_table_sequences)
        self.allow_play_in_front_of_players = bool(allow_play_in_front_of_players)
        self.allow_draw_from_discard = bool(allow_draw_from_discard)
        self.draw_from_discard_mode = (
            draw_from_discard_mode if draw_from_discard_mode in {"top", "any"} else "top"
        )
        self.allow_face_down_table_cards = bool(allow_face_down_table_cards)
        self.allow_move_table_sequences = bool(allow_move_table_sequences)
        self.allow_recycle_discard_to_deck = bool(allow_recycle_discard_to_deck)
        self.enable_chip_accounts = bool(enable_chip_accounts)
        self.minimum_bet = minimum_bet
        self.starting_balance = starting_balance
        self.require_pot_withdrawal_confirmation = bool(require_pot_withdrawal_confirmation)
        self.chip_balances = [starting_balance if enable_chip_accounts else 0 for _ in self.players]
        self.chip_pot = 0
        self.pending_pot_withdrawal = None
        self.undo_stack = []
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
        self.allow_positioned_play = bool(allow_positioned_play or allow_face_down_table_cards or allow_move_table_sequences)
        self.occupied_slot_action = (
            occupied_slot_action if occupied_slot_action in {"invalid", "swap"} else "invalid"
        )

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
            allow_positioned_play=self.allow_positioned_play,
            occupied_slot_action=self.occupied_slot_action,
            enable_undo=self.enable_undo,
            allow_move_cards_on_table=self.allow_move_cards_on_table,
            allow_play_in_front_of_players=self.allow_play_in_front_of_players,
            allow_draw_from_discard=self.allow_draw_from_discard,
            draw_from_discard_mode=self.draw_from_discard_mode,
            allow_face_down_table_cards=self.allow_face_down_table_cards,
            allow_move_table_sequences=self.allow_move_table_sequences,
            allow_recycle_discard_to_deck=self.allow_recycle_discard_to_deck,
            shared_discard_pile_count=self.shared_discard_pile_count,
            personal_discard_pile_count=self.personal_discard_pile_count,
            enable_chip_accounts=self.enable_chip_accounts,
            minimum_bet=self.minimum_bet,
            starting_balance=self.starting_balance,
            require_pot_withdrawal_confirmation=self.require_pot_withdrawal_confirmation,
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

    @property
    def discard_pile(self):
        """Backward-compatible alias for the first shared discard pile."""
        return self.discard_piles[0] if self.discard_piles else []

    @discard_pile.setter
    def discard_pile(self, cards):
        if not hasattr(self, "discard_piles") or not self.discard_piles:
            self.discard_piles = [cards]
        else:
            self.discard_piles[0] = cards

    def ensure_discard_pile_state(self):
        """Fill in discard-pile fields for sessions created by older versions."""
        shared = getattr(self, "discard_piles", None)
        if not isinstance(shared, list) or not shared:
            legacy_pile = self.__dict__.get("discard_pile", [])
            if not isinstance(legacy_pile, list):
                legacy_pile = []
            shared = [legacy_pile]
            self.discard_piles = shared
        self.shared_discard_pile_count = len(shared)

        personal_count = getattr(self, "personal_discard_pile_count", 0)
        if not isinstance(personal_count, int) or isinstance(personal_count, bool) or personal_count < 0:
            personal_count = 0
        self.personal_discard_pile_count = personal_count
        personal = getattr(self, "personal_discard_piles", None)
        if not isinstance(personal, list):
            personal = []
        personal = [
            (list(piles) if isinstance(piles, list) else [])[:personal_count]
            for piles in personal[:len(self.players)]
        ]
        while len(personal) < len(self.players):
            personal.append([])
        for piles in personal:
            piles.extend([] for _ in range(personal_count - len(piles)))
        self.personal_discard_piles = personal

    def all_discard_piles(self):
        self.ensure_discard_pile_state()
        piles = [(f"Shared discard {index + 1}", pile) for index, pile in enumerate(self.discard_piles)]
        for player_index, player_piles in enumerate(self.personal_discard_piles):
            name = self.players[player_index].name
            piles.extend((f"{name}'s discard {index + 1}", pile) for index, pile in enumerate(player_piles))
        return piles

    def discard_from_current(self, index, pile_index=0, personal=False):
        player = self.players[self.current_player_index]
        card = player.play_card(index)

        if card:
            destination = (
                self.personal_discard_piles[self.current_player_index][pile_index]
                if personal else self.discard_piles[pile_index]
            )
            destination.append(card)
            self.log_action(player.name, "discard", card)
            return card   # ✅ success
        else:
            return None   # ❌ failure

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

    def save_discard_pile(self, path):
        import os
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.discard_pile, f, indent=2)

    def save_session(self, path):
        from .gamesession import save_session
        return save_session(self, path)

    @classmethod
    def load_session(cls, path):
        from .gamesession import load_session
        return load_session(cls, path)
