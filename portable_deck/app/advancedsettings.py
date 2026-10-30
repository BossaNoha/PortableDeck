"""Advanced options panel for the settings window."""
import tkinter as tk
from ..ui.tooltip import add_tooltip


class AdvancedSettingsPanel:
    def __init__(self, parent, root, settings, fit_window):
        self.root = root
        self.fit_window = fit_window
        self.score_var = tk.BooleanVar(value=bool(settings.get("enable_score_counter", False)))
        self.confirmation_var = tk.BooleanVar(
            value=bool(settings.get("require_point_confirmation", False))
        )
        self.take_table_var = tk.BooleanVar(value=bool(settings.get("allow_take_from_table", False)))
        self.table_to_discard_var = tk.BooleanVar(
            value=bool(settings.get("allow_move_table_card_to_discard", False))
        )
        self.manual_cleanup_var = tk.BooleanVar(
            value=bool(settings.get("allow_manual_table_cleanup", False))
        )
        self.round_cleanup_var = tk.BooleanVar(
            value=bool(settings.get("clear_table_on_round_end", False))
        )
        self.positioned_play_var = tk.BooleanVar(
            value=bool(settings.get("allow_positioned_play", False))
        )
        self.move_table_cards_var = tk.BooleanVar(
            value=bool(settings.get("allow_move_cards_on_table", False))
        )
        self.play_in_front_var = tk.BooleanVar(
            value=bool(settings.get("allow_play_in_front_of_players", False))
        )
        self.draw_from_discard_var = tk.BooleanVar(
            value=bool(settings.get("allow_draw_from_discard", False))
        )
        mode = settings.get("draw_from_discard_mode", "top")
        self.discard_draw_mode_var = tk.StringVar(
            value="Take any card" if mode == "any" else "Take only the top card"
        )
        self.chip_accounts_var = tk.BooleanVar(
            value=bool(settings.get("enable_chip_accounts", False))
        )
        self.minimum_bet_var = tk.StringVar(value=str(settings.get("minimum_bet", 1)))
        self.starting_balance_var = tk.StringVar(value=str(settings.get("starting_balance", 100)))
        self.pot_confirmation_var = tk.BooleanVar(
            value=bool(settings.get("require_pot_withdrawal_confirmation", False))
        )
        self.occupied_slot_action_var = tk.StringVar(
            value=settings.get("occupied_slot_action", "invalid")
        )
        self.undo_var = tk.BooleanVar(value=bool(settings.get("enable_undo", False)))
        self.face_down_var = tk.BooleanVar(value=bool(settings.get("allow_face_down_table_cards", False)))
        self.move_sequences_var = tk.BooleanVar(value=bool(settings.get("allow_move_table_sequences", False)))
        self.recycle_discard_var = tk.BooleanVar(value=bool(settings.get("allow_recycle_discard_to_deck", False)))
        self.shared_discard_count_var = tk.StringVar(value=str(settings.get("shared_discard_pile_count", 1)))
        self.personal_discard_count_var = tk.StringVar(value=str(settings.get("personal_discard_pile_count", 0)))
        self.expanded_var = tk.BooleanVar(value=False)

        self.button = add_tooltip(
            tk.Button(parent, text="Advanced Settings ▸", command=self.toggle),
            "Expand optional scoring, table, undo, and chip-account settings.",
        )
        self.button.grid(row=7, column=0, columnspan=3, sticky="w", pady=(8, 2))
        self.frame = tk.LabelFrame(parent, text="Advanced Settings", padx=8, pady=5)
        self.frame.grid(row=8, column=0, columnspan=3, sticky="ew", pady=4)
        self.frame.grid_remove()
        self._build_controls()

    def _build_controls(self):
        columns = tk.Frame(self.frame)
        columns.grid(row=0, column=0, sticky="nsew")
        columns.columnconfigure(0, weight=1, uniform="advanced")
        columns.columnconfigure(1, weight=1, uniform="advanced")

        scoring = tk.LabelFrame(columns, text="Scoring and turn tools", padx=8, pady=5)
        scoring.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 6))
        add_tooltip(tk.Checkbutton(
            scoring,
            text="Enable score counters and point requests",
            variable=self.score_var,
        ), "Show each player's score and allow point requests.").pack(anchor="w")
        add_tooltip(tk.Checkbutton(scoring, text="Enable Undo", variable=self.undo_var), "Show Undo during a game and keep reversible action history.").pack(anchor="w")
        self.confirmation_check = tk.Checkbutton(
            scoring,
            text="Require approval from the other players for a point",
            variable=self.confirmation_var,
        )
        add_tooltip(self.confirmation_check, "Other players must approve a point request before it is awarded.").pack(anchor="w")

        chips = tk.LabelFrame(columns, text="Chip accounts", padx=8, pady=5)
        chips.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=(0, 6))

        deck_actions = tk.LabelFrame(columns, text="Deck actions", padx=8, pady=5)
        deck_actions.grid(row=1, column=1, sticky="nsew", padx=(4, 0), pady=(0, 6))
        draw_toggle = tk.Checkbutton(
            deck_actions,
            text="Allow drawing from the discard pile",
            variable=self.draw_from_discard_var,
            command=self.update_discard_draw_controls,
        )
        add_tooltip(draw_toggle, "Add an action that takes a card from the discard pile into the current hand.").pack(anchor="w")
        self.discard_draw_mode_menu = tk.OptionMenu(
            deck_actions, self.discard_draw_mode_var,
            "Take only the top card", "Take any card",
        )
        self.discard_draw_mode_menu.pack(anchor="w", padx=(20, 0))

        table = tk.LabelFrame(columns, text="Table actions", padx=8, pady=5)
        table.grid(row=1, column=0, sticky="nsew", padx=(0, 4), pady=(0, 6))
        table_options = tk.Frame(table)
        table_options.pack(fill="x")
        table_options.columnconfigure(0, weight=1, uniform="table-actions")
        table_options.columnconfigure(1, weight=1, uniform="table-actions")
        self._add_check(table_options, "Take a selected table card into the current hand", self.take_table_var, "Move a selected table card into the current player's hand.", row=0, column=0)
        self._add_check(table_options, "Move a selected table card to discard", self.table_to_discard_var, "Move a selected table card directly to the discard pile.", row=1, column=0)
        self._add_check(table_options, "Let the current player clear the table", self.manual_cleanup_var, "Add an action that sends all table cards to the discard pile.", row=2, column=0)
        self._add_check(table_options, "Clear the table at round end", self.round_cleanup_var, "Automatically discard all table cards when the last player ends the round.", row=3, column=0)
        self._add_check(table_options, "Play cards at specific table positions", self.positioned_play_var, "Choose an available empty position on the table when playing a card.", row=0, column=1)
        self._add_check(table_options, "Move cards between table positions", self.move_table_cards_var, "Move a card already on the table to another empty position.", row=1, column=1)
        self._add_check(table_options, "Play cards in front of any player", self.play_in_front_var, "Show a separate card row for each player and allow targeted plays.", row=2, column=1)
        self._add_check(table_options, "Allow face-down cards and flipping", self.face_down_var, "Play a card face down, then reveal it when it is the last face-down card in its column.", row=4, column=0)
        self._add_check(table_options, "Move face-up card sequences", self.move_sequences_var, "Move a face-up card and the cards below it together in the same column.", row=4, column=1)

        deck_recycle = tk.Checkbutton(
            deck_actions,
            text="Recycle discard pile when draw deck is empty",
            variable=self.recycle_discard_var,
            wraplength=280,
            justify="left",
            anchor="w",
        )
        add_tooltip(deck_recycle, "Add an action that returns the whole discard pile to the draw deck when it runs out.").pack(anchor="w", pady=(5, 0))
        discard_counts = tk.Frame(deck_actions)
        discard_counts.pack(anchor="w", fill="x", pady=(5, 0))
        add_tooltip(tk.Label(discard_counts, text="Shared discard piles:"), "Number of discard piles accessible to all players.").grid(row=0, column=0, sticky="w")
        tk.Spinbox(discard_counts, from_=1, to=20, width=5, textvariable=self.shared_discard_count_var).grid(row=0, column=1, padx=(6, 12))
        add_tooltip(tk.Label(discard_counts, text="Personal piles per player:"), "Each player gets this many private discard piles in addition to the shared piles.").grid(row=1, column=0, sticky="w")
        tk.Spinbox(discard_counts, from_=0, to=20, width=5, textvariable=self.personal_discard_count_var).grid(row=1, column=1, padx=(6, 12))

        occupied_row = tk.Frame(table_options)
        occupied_row.grid(row=3, column=1, sticky="w", pady=(3, 0))
        add_tooltip(tk.Label(occupied_row, text="Occupied spot:"), "Choose what happens if a selected table position already contains a card.").pack(side="left")
        add_tooltip(tk.OptionMenu(occupied_row, self.occupied_slot_action_var, "invalid", "swap"), "Invalid blocks the play; swap exchanges the hand card with the table card.").pack(side="left")

        chip_toggle = tk.Checkbutton(
            chips,
            text="Enable Chip Accounts",
            variable=self.chip_accounts_var,
            command=self.update_chip_settings_visibility,
        )
        add_tooltip(chip_toggle, "Enable per-player chip balances and a shared pot for betting-style play.").pack(anchor="w")
        self.chip_settings_frame = tk.Frame(chips)
        add_tooltip(tk.Label(self.chip_settings_frame, text="Minimum bet:"), "Reference minimum amount for a chip bet.").grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        add_tooltip(tk.Spinbox(
            self.chip_settings_frame,
            from_=1,
            to=1000000,
            width=10,
            textvariable=self.minimum_bet_var,
        ), "Minimum chip amount a player must put into the pot.").grid(row=0, column=1, sticky="w")
        add_tooltip(tk.Label(self.chip_settings_frame, text="Starting balance:"), "Chips each player receives in a new game.").grid(
            row=1, column=0, sticky="w", padx=(0, 8)
        )
        add_tooltip(tk.Spinbox(
            self.chip_settings_frame,
            from_=0,
            to=1000000000,
            width=10,
            textvariable=self.starting_balance_var,
        ), "Starting number of chips assigned to each player's account.").grid(row=1, column=1, sticky="w")
        add_tooltip(tk.Checkbutton(
            self.chip_settings_frame,
            text="Require other players to approve taking the pot",
            variable=self.pot_confirmation_var,
        ), "Require approval from every other player before the pot can be collected.").grid(row=2, column=0, columnspan=2, sticky="w", pady=(5, 0))

        self.score_var.trace_add("write", self.update_confirmation_control)
        self.update_confirmation_control()
        self.update_discard_draw_controls()
        self.update_chip_settings_visibility()

    def _add_check(self, parent, label, variable, help_text="", row=0, column=0):
        add_tooltip(
            tk.Checkbutton(
                parent, text=label, variable=variable, wraplength=260,
                justify="left", anchor="w",
            ),
            help_text,
        ).grid(row=row, column=column, sticky="w", padx=3, pady=2)

    def update_confirmation_control(self, *_):
        self.confirmation_check.config(state="normal" if self.score_var.get() else "disabled")

    def update_discard_draw_controls(self):
        self.discard_draw_mode_menu.config(
            state="normal" if self.draw_from_discard_var.get() else "disabled"
        )

    def update_chip_settings_visibility(self):
        if self.chip_accounts_var.get():
            self.chip_settings_frame.pack(anchor="w", padx=(22, 0))
        else:
            self.chip_settings_frame.pack_forget()
        self.root.after_idle(self.fit_window)

    def toggle(self):
        expanded = not self.expanded_var.get()
        self.expanded_var.set(expanded)
        if expanded:
            self.frame.grid()
            self.button.config(text="Advanced Settings ▾")
        else:
            self.frame.grid_remove()
            self.button.config(text="Advanced Settings ▸")
        self.root.after_idle(self.fit_window)

    def values(self):
        minimum_bet = int(self.minimum_bet_var.get())
        starting_balance = int(self.starting_balance_var.get())
        shared_discard_count = int(self.shared_discard_count_var.get())
        personal_discard_count = int(self.personal_discard_count_var.get())
        if minimum_bet < 1 or starting_balance < 0 or not 1 <= shared_discard_count <= 20 or not 0 <= personal_discard_count <= 20:
            raise ValueError
        return {
            "enable_score_counter": self.score_var.get(),
            "require_point_confirmation": self.score_var.get() and self.confirmation_var.get(),
            "allow_take_from_table": self.take_table_var.get(),
            "allow_move_table_card_to_discard": self.table_to_discard_var.get(),
            "allow_manual_table_cleanup": self.manual_cleanup_var.get(),
            "clear_table_on_round_end": self.round_cleanup_var.get(),
            "allow_positioned_play": self.positioned_play_var.get(),
            "allow_move_cards_on_table": self.move_table_cards_var.get(),
            "allow_move_table_sequences": self.move_sequences_var.get(),
            "allow_face_down_table_cards": self.face_down_var.get(),
            "allow_recycle_discard_to_deck": self.recycle_discard_var.get(),
            "shared_discard_pile_count": shared_discard_count,
            "personal_discard_pile_count": personal_discard_count,
            "allow_play_in_front_of_players": self.play_in_front_var.get(),
            "allow_draw_from_discard": self.draw_from_discard_var.get(),
            "draw_from_discard_mode": (
                "any" if self.discard_draw_mode_var.get() == "Take any card" else "top"
            ),
            "enable_chip_accounts": self.chip_accounts_var.get(),
            "minimum_bet": minimum_bet,
            "starting_balance": starting_balance,
            "require_pot_withdrawal_confirmation": (
                self.chip_accounts_var.get() and self.pot_confirmation_var.get()
            ),
            "occupied_slot_action": self.occupied_slot_action_var.get(),
            "enable_undo": self.undo_var.get(),
        }
