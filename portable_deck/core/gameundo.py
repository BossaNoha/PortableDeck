"""Undo snapshots and restoration for the Game model."""
import copy
from .player import Player

class GameUndoActions:

    def capture_undo_state(self):
        """Return the mutable game state needed to reverse one action."""
        return {
            "remaining_deck": copy.deepcopy(self.deck.flat_deck),
            "players": [
                {"name": player.name, "hand": copy.deepcopy(player.hand)}
                for player in self.players
            ],
            "discard_pile": copy.deepcopy(self.discard_pile),
            "discard_piles": copy.deepcopy(self.discard_piles),
            "personal_discard_piles": copy.deepcopy(self.personal_discard_piles),
            "table_cards": copy.deepcopy(self.table_cards),
            "current_player_index": self.current_player_index,
            "history": copy.deepcopy(self.history),
            "cards_drawn_this_turn": self.cards_drawn_this_turn,
            "scores": copy.deepcopy(self.scores),
            "pending_point_request": copy.deepcopy(self.pending_point_request),
            "gui_log": copy.deepcopy(self.gui_log),
            "chip_balances": copy.deepcopy(self.chip_balances),
            "chip_pot": self.chip_pot,
            "pending_pot_withdrawal": copy.deepcopy(self.pending_pot_withdrawal),
        }

    def undo_last_action(self):
        """Restore the state from immediately before the most recent action."""
        if not self.enable_undo or not self.undo_stack:
            return False
        state = self.undo_stack.pop()
        self.deck.flat_deck = copy.deepcopy(state["remaining_deck"])
        self.players = []
        for saved_player in state["players"]:
            player = Player(saved_player["name"])
            player.hand = copy.deepcopy(saved_player["hand"])
            self.players.append(player)
        self.discard_pile = copy.deepcopy(state["discard_pile"])
        self.discard_piles = copy.deepcopy(state.get("discard_piles", [state["discard_pile"]]))
        self.personal_discard_piles = copy.deepcopy(state.get(
            "personal_discard_piles",
            [[] for _ in self.players],
        ))
        self.table_cards = copy.deepcopy(state["table_cards"])
        self.current_player_index = state["current_player_index"]
        self.history = copy.deepcopy(state["history"])
        self.cards_drawn_this_turn = state["cards_drawn_this_turn"]
        self.scores = copy.deepcopy(state["scores"])
        self.pending_point_request = copy.deepcopy(state["pending_point_request"])
        self.gui_log = copy.deepcopy(state["gui_log"])
        self.chip_balances = copy.deepcopy(state.get("chip_balances", [0 for _ in self.players]))
        self.chip_pot = state.get("chip_pot", 0)
        self.pending_pot_withdrawal = copy.deepcopy(state.get("pending_pot_withdrawal"))
        return True

