"""Game options panel for the settings window."""
import tkinter as tk
from ..ui.tooltip import add_tooltip
from ..ui.collapsiblesection import CollapsibleSection
from ..ui.responsivesections import ResponsiveSections
from .personalpilesettings import PersonalPileSettings
from .rolesteamssettings import RolesTeamsSettings
from .interactionsettings import InteractionSettings
from .cardsvisibilitysettings import CardsVisibilitySettings
from .scorelimitssettings import ScoreLimitsSettings
from .playerleavingsettings import PlayerLeavingSettings
from .specialactionssettings import SpecialActionsSettings
from .flippingsettings import FlippingSettings


class GameSettingsPanel:
    def __init__(self, parent, root, settings, fit_window, players_var=None, player_name=None, custom_names_var=None, color_categories_var=None):
        self.color_categories_var = color_categories_var if color_categories_var is not None else tk.BooleanVar(value=settings.get("color_game_settings_categories", False))
        self.custom_names_var = custom_names_var if custom_names_var is not None else tk.BooleanVar(value=settings.get("use_custom_player_names", False))
        self.reset_chips_var = tk.BooleanVar(value=settings.get("reset_chip_accounts_on_restart", True))
        self.shared_chips_var = tk.BooleanVar(value=settings.get("share_team_chips", False))
        self.reduce_score_var = tk.BooleanVar(value=settings.get("allow_reduce_score", False))
        self.shared_score_var = tk.BooleanVar(value=settings.get("share_team_score", False))
        self.team_score_var = tk.BooleanVar(value=settings.get("enable_team_score", False))
        self.player_name = player_name
        self.settings = settings
        self.players_var = players_var or tk.StringVar(value=str(settings.get("num_players", 3)))
        self.table_limits_var = tk.BooleanVar(value=settings.get("enable_table_limits", False))
        self.limit_rows_var = tk.BooleanVar(value=settings.get("limit_table_rows", True))
        self.limit_columns_var = tk.BooleanVar(value=settings.get("limit_table_columns", True))
        self.table_rows_var = tk.StringVar(value=str(settings.get("max_table_rows", 3)))
        self.table_columns_var = tk.StringVar(value=str(settings.get("max_table_columns", 5)))
        self.table_enabled_var = tk.BooleanVar(value=settings.get("enable_table", True))
        self.discard_enabled_var = tk.BooleanVar(value=settings.get("enable_discard_pile", True))
        self.save_discard_var = tk.BooleanVar(value=settings.get("save_discard_on_exit", True))
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
        self.face_down_var = tk.BooleanVar(value=bool(settings.get("allow_face_down_table_cards", False)))
        self.move_sequences_var = tk.BooleanVar(value=bool(settings.get("allow_move_table_sequences", False)))
        self.recycle_discard_var = tk.BooleanVar(value=bool(settings.get("allow_recycle_discard_to_deck", False)))
        self.shared_discard_count_var = tk.StringVar(value=str(settings.get("shared_discard_pile_count", 1)))
        self.expanded_var = tk.BooleanVar(value=False)

        self.button = add_tooltip(
            tk.Button(parent, text="Game Settings ▸", command=self.toggle),
            "Expand optional scoring, table, discard pile, and chip-account settings.",
        )
        self.button.grid(row=7, column=0, columnspan=3, sticky="w", pady=(8, 2))
        self.frame = tk.LabelFrame(parent, text="Game Settings", padx=8, pady=5)
        self.frame.grid(row=8, column=0, columnspan=3, sticky="ew", pady=4)
        self.frame.grid_remove()
        self._build_controls()

    def _build_controls(self):
        self.category_layout = ResponsiveSections(self.frame)
        self.category_layout.grid(row=0, column=0, sticky="ew")
        self.frame.columnconfigure(0, weight=1)
        self.sections = self.category_layout.sections

        def section(title):
            panel = CollapsibleSection(self.category_layout, title, self.category_changed)
            self.category_layout.add(panel)
            return panel.content

        scoring = section("Scoring")
        add_tooltip(tk.Checkbutton(
            scoring,
            text="Enable score counters and point requests",
            variable=self.score_var,
        ), "Show each player's score and allow point requests.").pack(anchor="w")
        self.confirmation_check = tk.Checkbutton(
            scoring,
            text="Require approval from the other players for a point",
            variable=self.confirmation_var,
        )
        add_tooltip(self.confirmation_check, "Other players must approve a point request before it is awarded.").pack(anchor="w")

        self.reduce_score_check = tk.Checkbutton(scoring, text="Enable Reduce score", variable=self.reduce_score_var)
        self.reduce_score_check.pack(anchor="w")
        self.shared_score_check = tk.Checkbutton(scoring, text="Shared score within team", variable=self.shared_score_var)
        self.shared_score_check.pack(anchor="w")
        self.team_score_check = tk.Checkbutton(scoring, text="Score for team", variable=self.team_score_var)
        self.team_score_check.pack(anchor="w")
        self.score_limits = ScoreLimitsSettings(scoring, self.settings, self.score_var)
        chips = section("Chip accounts")

        discard_section = section("Discard pile")
        tk.Checkbutton(discard_section, text="Enable discard pile", variable=self.discard_enabled_var,
                       command=self.update_feature_controls).pack(anchor="w")
        self.discard_options = tk.Frame(discard_section)
        self.discard_options.pack(fill="x")
        discard_pile = self.discard_options
        add_tooltip(tk.Checkbutton(
            discard_pile,
            text="Save discard pile when the game window closes",
            variable=self.save_discard_var,
            wraplength=280, justify="left", anchor="w",
        ), "Save the discard pile to the app's internal data when exiting the app.").pack(anchor="w")
        draw_toggle = tk.Checkbutton(
            discard_pile,
            text="Allow drawing from the discard pile",
            variable=self.draw_from_discard_var,
            command=self.update_discard_draw_controls,
        )
        add_tooltip(draw_toggle, "Add an action that takes a card from the discard pile into the current hand.").pack(anchor="w")
        self.discard_draw_mode_menu = tk.OptionMenu(
            discard_pile, self.discard_draw_mode_var,
            "Take only the top card", "Take any card",
        )
        self.discard_draw_mode_menu.pack(anchor="w", padx=(20, 0))

        table_section = section("Table")
        tk.Checkbutton(table_section, text="Enable table", variable=self.table_enabled_var,
                       command=self.update_feature_controls).pack(anchor="w")
        self.table_options = tk.Frame(table_section)
        self.table_options.pack(fill="x")
        self.table_settings_section = CollapsibleSection(self.table_options, "Table settings", self.category_changed)
        self.table_settings_section.pack(fill="x", pady=(4, 0))
        self.table_actions_section = CollapsibleSection(self.table_options, "Table actions", self.category_changed)
        self.table_actions_section.pack(fill="x", pady=(4, 0))
        table = self.table_settings_section.content
        tk.Checkbutton(table, text="Limit table rows and columns", variable=self.table_limits_var,
                       command=self.update_feature_controls).pack(anchor="w")
        self.table_dimensions = tk.Frame(table)
        self.table_dimensions.pack(anchor="w", padx=18, pady=(0, 5))
        self.dimension_inputs = []
        for row, (label, variable, enabled) in enumerate((("Maximum rows:", self.table_rows_var, self.limit_rows_var),
                                                        ("Maximum columns:", self.table_columns_var, self.limit_columns_var))):
            tk.Checkbutton(self.table_dimensions, text=label, variable=enabled,
                           command=self.update_feature_controls).grid(row=row, column=0, sticky="w")
            entry = tk.Spinbox(self.table_dimensions, from_=1, to=20, width=5, textvariable=variable)
            entry.grid(row=row, column=1)
            self.dimension_inputs.append((entry, enabled))
        placement_options = tk.Frame(table)
        placement_options.pack(fill="x")
        placement_options.columnconfigure(0, weight=1)
        table_options = tk.Frame(self.table_actions_section.content)
        table_options.pack(fill="x")
        table_options.columnconfigure(0, weight=1)
        self._add_check(table_options, "Take a selected table card into the current hand", self.take_table_var, "Move a selected table card into the current player's hand.", row=0, column=0)
        self.table_to_discard_check = self._add_check(table_options, "Discard a selected table card to discard pile", self.table_to_discard_var, "Move a selected table card directly to the discard pile.", row=1, column=0)
        self._add_check(table_options, "Let the current player clear the table", self.manual_cleanup_var, "Add an action that sends all table cards to the discard pile.", row=2, column=0)
        self._add_check(table_options, "Clear the table at round end", self.round_cleanup_var, "Automatically discard all table cards when the last player ends the round.", row=3, column=0)
        self._add_check(placement_options, "Play cards at specific table positions", self.positioned_play_var, "Choose an available empty position on the table when playing a card.", row=0, column=0)
        self._add_check(table_options, "Move cards between table positions", self.move_table_cards_var, "Move a card already on the table to another empty position.", row=5, column=0)
        self._add_check(placement_options, "Play cards in front of any player", self.play_in_front_var, "Show a separate card row for each player and allow targeted plays.", row=1, column=0)
        self.face_down_check = self._add_check(table_options, "Allow playing face-down cards", self.face_down_var, "Play a card face down. Requires Flipping cards.", row=7, column=0)
        self._add_check(table_options, "Move face-up card sequences", self.move_sequences_var, "Move a face-up card and the cards below it together in the same column.", row=8, column=0)

        deck_recycle = tk.Checkbutton(
            discard_pile,
            text="Recycle discard pile when draw deck is empty",
            variable=self.recycle_discard_var,
            wraplength=280,
            justify="left",
            anchor="w",
        )
        add_tooltip(deck_recycle, "Add an action that returns the whole discard pile to the draw deck when it runs out.").pack(anchor="w", pady=(5, 0))
        discard_counts = tk.Frame(discard_pile)
        discard_counts.pack(anchor="w", fill="x", pady=(5, 0))
        add_tooltip(tk.Label(discard_counts, text="Shared discard piles:"), "Number of discard piles accessible to all players.").grid(row=0, column=0, sticky="w")
        tk.Spinbox(discard_counts, from_=1, to=20, width=5, textvariable=self.shared_discard_count_var).grid(row=0, column=1, padx=(6, 12))


        occupied_row = tk.Frame(placement_options)
        occupied_row.grid(row=2, column=0, sticky="w", pady=(3, 0))
        add_tooltip(tk.Label(occupied_row, text="Occupied spot:"), "Choose what happens if a selected table position already contains a card.").pack(side="left")
        add_tooltip(tk.OptionMenu(occupied_row, self.occupied_slot_action_var, "invalid", "swap"), "Invalid blocks the play; swap exchanges the hand card with the table card.").pack(side="left")

        chip_toggle = tk.Checkbutton(
            chips,
            text="Enable Chip Accounts",
            variable=self.chip_accounts_var,
            command=self.update_chip_settings_controls,
        )
        add_tooltip(chip_toggle, "Enable per-player chip balances and a shared pot for betting-style play.").pack(anchor="w")
        self.shared_chips_check = tk.Checkbutton(chips, text="Shared chips within team", variable=self.shared_chips_var)
        self.shared_chips_check.pack(anchor="w")
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

        tk.Checkbutton(self.chip_settings_frame, text="Reset chip accounts on game restart",
                       variable=self.reset_chips_var, wraplength=280, justify="left").grid(
                           row=3, column=0, columnspan=2, sticky="w", pady=(5, 0))

        personal = section("Personal piles on table")
        self.personal_piles = PersonalPileSettings(personal, self.settings, self.players_var, self.category_layout.schedule_layout, self.player_name)

        roles = section("Roles/teams")
        self.roles_teams = RolesTeamsSettings(roles, self.settings, self.players_var,
                                             self.custom_names_var, self.player_name,
                                             self.category_layout.schedule_layout)

        self.personal_piles.roles = self.roles_teams
        for variable in (self.roles_teams.enabled_var, self.roles_teams.teams_var, self.roles_teams.dealer_var):
            variable.trace_add("write", self.personal_piles.update_states)
        self.personal_piles.update_states()

        interactions = section("Player interactions")
        self.interactions = InteractionSettings(interactions, self.settings, self.chip_accounts_var, self.discard_enabled_var)

        visibility = section("Cards visibility")
        self.cards_visibility = CardsVisibilitySettings(visibility, self.settings, self.players_var, self.player_name, self.roles_teams)

        leaving = section("Leaving session")
        self.player_leaving = PlayerLeavingSettings(leaving, self.settings, self.score_var, self.chip_accounts_var, self.score_limits)

        special = section("Special actions")
        self.special_actions = SpecialActionsSettings(special, self.settings, self.discard_enabled_var)

        flipping = section("Flipping cards")
        self.flipping = FlippingSettings(flipping, self.settings, self.table_enabled_var, self.play_in_front_var)

        self.flipping.enabled.trace_add("write", self.update_feature_controls)

        self.section_states = {
            "Flipping cards": (self.flipping.enabled,),
            "Special actions": (self.special_actions.enabled,),
            "Scoring": (self.score_var,),
            "Chip accounts": (self.chip_accounts_var,),
            "Discard pile": (self.discard_enabled_var,),
            "Table": (self.table_enabled_var,),
            "Personal piles on table": (self.personal_piles.enabled_var,),
            "Roles/teams": (self.roles_teams.enabled_var,),
            "Player interactions": (self.interactions.enabled,),
            "Cards visibility": (self.cards_visibility.enabled,),
            "Leaving session": (self.player_leaving.enabled, self.player_leaving.allow_return),
        }
        for variables in self.section_states.values():
            for variable in variables:
                variable.trace_add("write", self.update_section_colors)
        self.color_categories_var.trace_add("write", self.update_section_colors)
        self.update_section_colors()

        for variable in (self.roles_teams.enabled_var, self.roles_teams.teams_var,
                         self.score_var, self.chip_accounts_var):
            variable.trace_add("write", self.update_team_options)
        self.update_team_options()
        self.score_var.trace_add("write", self.update_confirmation_control)
        self.update_confirmation_control()
        self.update_discard_draw_controls()
        self.update_chip_settings_controls()
        self.update_feature_controls()

    def update_section_colors(self, *_):
        for section in self.sections:
            section.set_enabled_indicator(any(variable.get() for variable in self.section_states[section.title]), self.color_categories_var.get())

    def update_team_options(self, *_):
        teams = self.roles_teams.enabled_var.get() and self.roles_teams.teams_var.get()
        self.shared_chips_check.configure(state="normal" if teams and self.chip_accounts_var.get() else "disabled")
        for check in (self.shared_score_check, self.team_score_check):
            check.configure(state="normal" if teams and self.score_var.get() else "disabled")

    def category_changed(self):
        self.category_layout.schedule_layout()
        self.root.after_idle(self.fit_window)

    def preferred_width(self):
        return self.category_layout.preferred_width() + 20

    def update_feature_controls(self, *_):
        for frame, enabled in ((self.table_settings_section.content, self.table_enabled_var.get()),
                               (self.table_actions_section.content, self.table_enabled_var.get()),
                               (self.discard_options, self.discard_enabled_var.get())):
            self._set_controls_enabled(frame, enabled)
        self._set_controls_enabled(self.table_dimensions, self.table_enabled_var.get() and self.table_limits_var.get())
        for entry, enabled in self.dimension_inputs:
            entry.configure(state="normal" if self.table_enabled_var.get() and self.table_limits_var.get() and enabled.get() else "disabled")
        self.update_discard_draw_controls()
        self.face_down_check.configure(state="normal" if self.table_enabled_var.get() and self.flipping.enabled.get() else "disabled")
        self.table_to_discard_check.configure(
            state="normal" if self.table_enabled_var.get() and self.discard_enabled_var.get() else "disabled"
        )

    def _set_controls_enabled(self, frame, enabled):
        for widget in frame.winfo_children():
            if "state" in widget.keys():
                widget.configure(state="normal" if enabled else "disabled")
            self._set_controls_enabled(widget, enabled)

    def _add_check(self, parent, label, variable, help_text="", row=0, column=0):
        check = add_tooltip(
            tk.Checkbutton(
                parent, text=label, variable=variable, wraplength=260,
                justify="left", anchor="w",
            ),
            help_text,
        )
        check.grid(row=row, column=column, sticky="w", padx=3, pady=2)
        return check

    def update_confirmation_control(self, *_):
        self.confirmation_check.config(state="normal" if self.score_var.get() else "disabled")
        self.reduce_score_check.config(state="normal" if self.score_var.get() else "disabled")

    def update_discard_draw_controls(self):
        self.discard_draw_mode_menu.config(
            state="normal" if self.discard_enabled_var.get() and self.draw_from_discard_var.get() else "disabled"
        )

    def update_chip_settings_controls(self):
        self.chip_settings_frame.pack(anchor="w", padx=(22, 0))
        self._set_controls_enabled(self.chip_settings_frame, self.chip_accounts_var.get())

    def toggle(self):
        expanded = not self.expanded_var.get()
        self.expanded_var.set(expanded)
        if expanded:
            self.frame.grid()
            self.button.config(text="Game Settings ▾")
        else:
            self.frame.grid_remove()
            self.button.config(text="Game Settings ▸")
        self.root.after_idle(self.fit_window)

    def values(self):
        minimum_bet = int(self.minimum_bet_var.get())
        starting_balance = int(self.starting_balance_var.get())
        shared_discard_count = int(self.shared_discard_count_var.get())
        if minimum_bet < 1 or starting_balance < 0 or not 1 <= shared_discard_count <= 20:
            raise ValueError
        rows, columns = int(self.table_rows_var.get()), int(self.table_columns_var.get())
        if not 1 <= rows <= 20 or not 1 <= columns <= 20:
            raise ValueError("Maximum table rows and columns must be between 1 and 20.")
        return {
            "limit_table_rows": self.limit_rows_var.get(),
            "limit_table_columns": self.limit_columns_var.get(),
            "enable_table_limits": self.table_limits_var.get(),
            "max_table_rows": rows, "max_table_columns": columns,
            **self.score_limits.values(),
            **self.player_leaving.values(),
            **self.special_actions.values(),
            **self.flipping.values(),
            "allow_reduce_score": self.reduce_score_var.get(),
            "share_team_chips": self.shared_chips_var.get(),
            "share_team_score": self.shared_score_var.get(),
            "enable_team_score": self.team_score_var.get(),
            "enable_table": self.table_enabled_var.get(),
            "enable_discard_pile": self.discard_enabled_var.get(),
            "save_discard_on_exit": self.save_discard_var.get(),
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
            "personal_discard_pile_count": 0,
            **self.personal_piles.values(),
            **self.roles_teams.values(),
            **self.interactions.values(),
            **self.cards_visibility.values(),
            "allow_play_in_front_of_players": self.play_in_front_var.get(),
            "allow_draw_from_discard": self.draw_from_discard_var.get(),
            "draw_from_discard_mode": (
                "any" if self.discard_draw_mode_var.get() == "Take any card" else "top"
            ),
            "reset_chip_accounts_on_restart": self.reset_chips_var.get(),
            "enable_chip_accounts": self.chip_accounts_var.get(),
            "minimum_bet": minimum_bet,
            "starting_balance": starting_balance,
            "require_pot_withdrawal_confirmation": (
                self.chip_accounts_var.get() and self.pot_confirmation_var.get()
            ),
            "occupied_slot_action": self.occupied_slot_action_var.get(),
        }
