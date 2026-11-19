"""Actions for chip accounts and the shared pot."""
from functools import wraps
import tkinter as tk
from tkinter import messagebox, simpledialog

from .chipdialogs import ask_chip_purchase, ask_pot_recipient
from ..core.chipoptions import build_chip_options


def session_action(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        return self.gui.run_action(lambda: method(self, *args, **kwargs))
    return wrapped


class ChipBankUI:
    """Build chip controls and connect them to the game's account actions."""

    def __init__(self, game_gui, parent):
        self.gui = game_gui
        self.buttons = []
        if not build_chip_options(self.gui.game).enabled:
            return
        self.buy_button = tk.Button(parent, text="Buy Chips", command=self.buy_chips)
        self.play_button = tk.Button(parent, text="Play Chips", command=self.play_chips)
        self.take_button = tk.Button(parent, text="Take Pot", command=self.take_pot)
        for button in (self.buy_button, self.play_button, self.take_button):
            button.pack(side="left", padx=5)
        self.buttons = [self.buy_button, self.play_button, self.take_button]
        self.update_action_buttons()

    @session_action
    def buy_chips(self):
        game = self.gui.game
        options = build_chip_options(game)
        if not self._check_available("buy_chips", options):
            return
        purchase = ask_chip_purchase(
            self.gui.root,
            options,
        )
        if purchase is None:
            return
        player_index, amount = purchase
        result = game.session.execute("buy_chips", player_index=player_index, amount=amount)
        if not result.success:
            messagebox.showerror(
                "Purchase failed", result.message, parent=self.gui.root
            )
        return result

    @session_action
    def play_chips(self):
        game = self.gui.game
        options = build_chip_options(game)
        if not self._check_available("play_chips", options):
            return
        amount = simpledialog.askinteger(
            "Play Chips",
            f"How many chips do you want to put in the pot?\nMinimum bet: {options.minimum_bet}",
            minvalue=options.minimum_bet,
            maxvalue=options.maximum_bet,
            parent=self.gui.root,
        )
        if amount is None:
            return
        result = game.session.execute("play_chips", amount=amount)
        if not result.success:
            messagebox.showwarning("Could not play chips", result.message, parent=self.gui.root)
        return result

    @session_action
    def take_pot(self):
        game = self.gui.game
        options = build_chip_options(game)
        if not self._check_available("take_pot", options):
            return
        recipient_index = ask_pot_recipient(
            self.gui.root, options
        )
        if recipient_index is None:
            return
        result = game.session.execute("take_pot", player_index=recipient_index)
        if not result.success:
            messagebox.showwarning("Could not take pot", result.message, parent=self.gui.root)
        return result

    def _check_available(self, action, options):
        available = getattr(options, action)
        if not available.allowed:
            messagebox.showwarning("Action unavailable", available.reason, parent=self.gui.root)
        return available.allowed

    def update_action_buttons(self):
        if not self.buttons:
            return
        options = build_chip_options(self.gui.game)
        for button, action in ((self.buy_button, "buy_chips"), (self.play_button, "play_chips"),
                               (self.take_button, "take_pot")):
            button.config(state="normal" if getattr(options, action).allowed else "disabled")
