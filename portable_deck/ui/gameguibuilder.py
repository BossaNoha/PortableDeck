"""Build the widgets that make up the main game window."""
import tkinter as tk
from .handframe import HandFrame
from .statuspanel import StatusPanel
from .tableframe import TableFrame
from .chipbankui import ChipBankUI
from ..app.deckpreview import show_deck_preview
from .cardactions import (
    clear_table, draw_card, discard_selected, end_turn,
    move_selected_table_card_to_discard, move_selected_table_card,
    play_at_selected_spot, play_selected, take_selected_from_table, draw_from_discard,
    play_selected_face_down, flip_selected_table_card, recycle_discard_into_deck,
)

class GameGUIBuilder:
    def build_game_interface(self):
        self.layout_frame = tk.Frame(self.root)
        self.layout_frame.pack(fill="both", expand=True)
        self.left_frame = tk.Frame(self.layout_frame)
        self.left_frame.pack(side="left", fill="both", expand=True)
        self.right_frame = tk.Frame(self.layout_frame)
        self.right_frame.pack(side="right", fill="y", padx=(0, 10), pady=5)

        # Status, hand, actions, and log stay together on the left.
        self.status_panel = StatusPanel(self.left_frame, self.game)
        self.status_panel.pack(padx=10, pady=5, fill="x")

        self.hand_frame = HandFrame(self.left_frame, self)
        self.hand_frame.pack(padx=10, pady=5, fill="x")

        self.actions_frame = tk.LabelFrame(self.left_frame, text="Actions", padx=5, pady=5)
        self.actions_frame.pack(padx=10, pady=5, fill="x")
        self.card_actions_frame = tk.Frame(self.actions_frame)
        self.card_actions_frame.pack(fill="x")
        self.turn_actions_frame = tk.Frame(self.actions_frame)
        self.turn_actions_frame.pack(fill="x")

        self.log_frame = tk.LabelFrame(self.left_frame, text="Game Log", padx=5, pady=5)
        self.log_frame.pack(padx=10, pady=5, fill="both", expand=True)

        self.log_text = tk.Text(self.log_frame, height=10, state="disabled")
        self.log_text.pack(fill="both", expand=True)

        self.table_frame = TableFrame(self.right_frame, self.game)
        self.table_frame.pack(fill="both", expand=True)

        # ----- Action buttons -----
        self.draw_button = tk.Button(
            self.card_actions_frame,
            text="Draw Card",
            command=lambda: self.run_action(
                draw_card, self.game, self.hand_frame, self.log, self.status_panel
            ),
        )
        self.draw_button.pack(side="left", padx=5)

        self.recycle_discard_button = None
        if self.game.allow_recycle_discard_to_deck:
            self.recycle_discard_button = tk.Button(
                self.card_actions_frame,
                text="Recycle Discard into Deck",
                command=lambda: self.run_action(
                    recycle_discard_into_deck, self.game, self.log,
                    self.status_panel, self.root,
                ),
            )
            self.recycle_discard_button.pack(side="left", padx=5)

        self.discard_draw_button = None
        if self.game.allow_draw_from_discard:
            self.discard_draw_button = tk.Button(
                self.card_actions_frame,
                text="Take from Discard",
                command=lambda: self.run_action(
                    draw_from_discard,
                    self.game, self.hand_frame, self.log, self.status_panel, self.root,
                ),
            )
            self.discard_draw_button.pack(side="left", padx=5)

        self.discard_button = tk.Button(
            self.card_actions_frame,
            text="Discard Selected",
            command=lambda: self.run_action(
                discard_selected, self.game, self.hand_frame, self.log, self.status_panel
            ),
        )
        self.discard_button.pack(side="left", padx=5)

        self.play_button = tk.Button(
            self.card_actions_frame,
            text="Play Selected Card",
            command=lambda: self.run_action(
                play_selected, self.game, self.hand_frame, self.table_frame, self.log, self.status_panel
            ),
        )
        self.play_button.pack(side="left", padx=5)

        if self.game.allow_face_down_table_cards:
            self.play_face_down_button = tk.Button(
                self.card_actions_frame,
                text="Play Selected Face Down",
                command=lambda: self.run_action(
                    play_selected_face_down, self.game, self.hand_frame,
                    self.table_frame, self.log, self.status_panel,
                ),
            )
            self.play_face_down_button.pack(side="left", padx=5)

        self.positioned_play_buttons = []
        if self.game.allow_positioned_play or self.game.allow_play_in_front_of_players:
            self.play_at_spot_button = tk.Button(
                self.card_actions_frame,
                text="Play at Selected Spot",
                command=lambda: self.run_action(
                    play_at_selected_spot,
                    self.game, self.hand_frame, self.table_frame, self.log, self.status_panel,
                ),
            )
            self.play_at_spot_button.pack(side="left", padx=5)
            self.positioned_play_buttons.append(self.play_at_spot_button)

        self.table_action_buttons = []
        if self.game.allow_take_from_table:
            self.take_table_button = tk.Button(
                self.card_actions_frame,
                text="Take Selected from Table",
                command=lambda: self.run_action(
                    take_selected_from_table,
                    self.game, self.table_frame, self.hand_frame, self.log, self.status_panel,
                ),
            )
            self.take_table_button.pack(side="left", padx=5)
            self.table_action_buttons.append(self.take_table_button)
        if self.game.allow_move_table_card_to_discard:
            self.table_discard_button = tk.Button(
                self.card_actions_frame,
                text="Move Selected to Discard",
                command=lambda: self.run_action(
                    move_selected_table_card_to_discard,
                    self.game, self.table_frame, self.log, self.status_panel,
                ),
            )
            self.table_discard_button.pack(side="left", padx=5)
            self.table_action_buttons.append(self.table_discard_button)
        if self.game.allow_move_cards_on_table or self.game.allow_move_table_sequences:
            self.move_table_card_button = tk.Button(
                self.card_actions_frame,
                text="Move Selected Table Card",
                command=lambda: self.run_action(
                    move_selected_table_card,
                    self.game, self.table_frame, self.log, self.status_panel,
                ),
            )
            self.move_table_card_button.pack(side="left", padx=5)
            self.table_action_buttons.append(self.move_table_card_button)
        if self.game.allow_face_down_table_cards:
            self.flip_table_card_button = tk.Button(
                self.card_actions_frame,
                text="Flip Selected Table Card",
                command=lambda: self.run_action(
                    flip_selected_table_card, self.game, self.table_frame,
                    self.log, self.status_panel,
                ),
            )
            self.flip_table_card_button.pack(side="left", padx=5)
            self.table_action_buttons.append(self.flip_table_card_button)
        if self.game.allow_manual_table_cleanup:
            self.clear_table_button = tk.Button(
                self.card_actions_frame,
                text="Clear Table",
                command=lambda: self.run_action(
                    clear_table, self.game, self.table_frame, self.log, self.status_panel
                ),
            )
            self.clear_table_button.pack(side="left", padx=5)
            self.table_action_buttons.append(self.clear_table_button)

        self.next_button = tk.Button(
            self.turn_actions_frame,
            text="Next Turn",
            command=lambda: self.run_action(
                end_turn,
                self.game, self.hand_frame, self.log, self.status_panel, self.handle_turn_start,
            ),
        )
        self.next_button.pack(side="left", padx=5)

        if self.game.enable_undo:
            self.undo_button = tk.Button(
                self.turn_actions_frame,
                text="Undo",
                command=self.undo,
                state="disabled",
            )
            self.undo_button.pack(side="left", padx=5)

        self.save_button = tk.Button(self.turn_actions_frame, text="Save", command=self.save)
        self.save_button.pack(side="left", padx=5)

        self.view_deck_button = tk.Button(
            self.turn_actions_frame,
            text="View Full Deck",
            command=lambda: show_deck_preview(self.root, self.game.deck),
        )
        self.view_deck_button.pack(side="left", padx=5)

        self.chip_bank_ui = ChipBankUI(self, self.turn_actions_frame)

        self.menu_button = tk.Button(
            self.turn_actions_frame, text="Exit to Main Menu", command=self.exit_to_menu
        )
        self.menu_button.pack(side="left", padx=5)

        self.desktop_button = tk.Button(
            self.turn_actions_frame, text="Exit to Desktop", command=self.exit_to_desktop
        )
        self.desktop_button.pack(side="left", padx=5)

        self.restart_button = tk.Button(
            self.turn_actions_frame, text="Restart Game", command=self.restart
        )
        self.restart_button.pack(side="left", padx=5)

        if self.game.score_enabled:
            self.point_button = tk.Button(
                self.turn_actions_frame,
                text="Request Point",
                command=self.request_current_point,
            )
            self.point_button.pack(side="left", padx=5)

        # Initialize GUI
        self.hand_frame.update_hand()
        self.status_panel.update_status()
        if self.game.gui_log:
            self._restore_log()
        else:
            self.log(f"{self.current_player_name()}'s turn starts.")
        turn_start_state = (
            self.game.capture_undo_state() if self.game.enable_undo else None
        )
        self.handle_turn_start()
        self._record_undo_state(turn_start_state)
        self.update_point_button()
        self.update_undo_button()
        self.update_chip_action_buttons()
        self.checkpoint()

