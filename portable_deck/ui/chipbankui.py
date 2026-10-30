"""Actions for chip accounts and the shared pot."""
import tkinter as tk
from tkinter import messagebox, simpledialog

from .chipdialogs import ask_chip_purchase, ask_pot_recipient


class ChipBankUI:
    """Build chip controls and connect them to the game's account actions."""

    def __init__(self, game_gui, parent):
        self.gui = game_gui
        self.buttons = []
        if not self.gui.game.enable_chip_accounts:
            return
        self.buy_button = tk.Button(parent, text="Buy Chips", command=self.buy_chips)
        self.play_button = tk.Button(parent, text="Play Chips", command=self.play_chips)
        self.take_button = tk.Button(parent, text="Take Pot", command=self.take_pot)
        for button in (self.buy_button, self.play_button, self.take_button):
            button.pack(side="left", padx=5)
        self.buttons = [self.buy_button, self.play_button, self.take_button]
        self.update_action_buttons()

    def buy_chips(self):
        game = self.gui.game
        purchase = ask_chip_purchase(
            self.gui.root,
            game.players,
            game.current_player_index,
            max(1, game.minimum_bet),
        )
        if purchase is None:
            return
        player_index, amount = purchase
        undo_state = game.capture_undo_state() if game.enable_undo else None
        balance = game.buy_chips(player_index, amount)
        if balance is None:
            messagebox.showerror(
                "Purchase failed", "Could not add chips to this account.", parent=self.gui.root
            )
            return
        player_name = game.players[player_index].name
        self._finish_action(
            undo_state, f"{player_name} bought {amount} chips. New balance: {balance}."
        )

    def play_chips(self):
        game = self.gui.game
        balance = game.chip_balances[game.current_player_index]
        if balance < game.minimum_bet:
            messagebox.showwarning(
                "Not enough chips",
                f"You need at least {game.minimum_bet} chips to play a bet.",
                parent=self.gui.root,
            )
            return
        amount = simpledialog.askinteger(
            "Play Chips",
            f"How many chips do you want to put in the pot?\nMinimum bet: {game.minimum_bet}",
            minvalue=game.minimum_bet,
            maxvalue=balance,
            parent=self.gui.root,
        )
        if amount is None:
            return
        undo_state = game.capture_undo_state() if game.enable_undo else None
        succeeded, message = game.play_chips(amount)
        if not succeeded:
            messagebox.showwarning("Could not play chips", message, parent=self.gui.root)
            return
        self._finish_action(undo_state, message)

    def take_pot(self):
        game = self.gui.game
        if game.chip_pot < 1:
            messagebox.showinfo(
                "Pot is empty", "There are no chips to take yet.", parent=self.gui.root
            )
            return
        if game.pending_pot_withdrawal is not None:
            messagebox.showinfo(
                "Approval pending",
                "A pot withdrawal is already waiting for the other players.",
                parent=self.gui.root,
            )
            return
        recipient_index = ask_pot_recipient(
            self.gui.root, game.players, game.current_player_index, game.chip_pot
        )
        if recipient_index is None:
            return
        undo_state = game.capture_undo_state() if game.enable_undo else None
        succeeded, message = game.request_pot_withdrawal(recipient_index)
        if not succeeded:
            messagebox.showwarning("Could not take pot", message, parent=self.gui.root)
            return
        self._finish_action(undo_state, message)

    def _finish_action(self, undo_state, message):
        self.gui.log(message)
        self.gui._record_undo_state(undo_state)
        self.gui.status_panel.update_status()
        self.gui.update_undo_button()
        self.update_action_buttons()
        self.gui.checkpoint()

    def update_action_buttons(self):
        if not self.buttons:
            return
        game = self.gui.game
        can_play = (
            game.pending_pot_withdrawal is None
            and game.chip_balances[game.current_player_index] >= game.minimum_bet
        )
        self.play_button.config(state="normal" if can_play else "disabled")
        can_take = game.chip_pot > 0 and game.pending_pot_withdrawal is None
        self.take_button.config(state="normal" if can_take else "disabled")
