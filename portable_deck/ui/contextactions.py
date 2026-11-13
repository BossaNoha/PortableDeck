"""Optional contextual card controls and compact session menus."""
import tkinter as tk

class ContextActions:
    def __init__(self, gui):
        self.gui = gui
        self.buttons = list(gui.card_actions_frame.winfo_children())
        self.menus = {}
        for button in self.buttons + list(gui.turn_actions_frame.winfo_children()):
            button.pack_forget()
        gui.next_button.pack(side="left", padx=5)
        if hasattr(gui, "undo_button"):
            gui.undo_button.pack(side="left", padx=5)
        self.add_menu("Players", [getattr(getattr(gui, "interactions_ui", None), "button", None),
                                   getattr(gui, "leave_session_button", None), getattr(gui, "return_player_button", None)])
        self.add_menu("Chips", gui.chip_bank_ui.buttons)
        self.add_menu("Score", [getattr(gui, "point_button", None), getattr(gui, "reduce_score_button", None)])
        self.add_menu("Table", [getattr(gui, "clear_table_button", None), getattr(gui, "recycle_discard_button", None)])
        self.add_menu("View", [gui.view_deck_button, getattr(gui, "visible_hands_button", None)])
        if hasattr(gui, "interactions_ui") and gui.game.interaction_allowed("give_card"):
            self.give_button = tk.Button(gui.card_actions_frame, text="Give to player…",
                                         command=lambda: gui.interactions_ui.show("give_card"))
            self.buttons.append(self.give_button)
        gui.card_actions_frame.pack_propagate(False)
        gui.card_actions_frame.configure(width=1)
        gui.card_actions_frame.bind("<Configure>", lambda e: self.layout())
        gui.table_frame.on_selection_changed = self.refresh
        self.shown = []
        self.refresh()

    def add_menu(self, title, buttons):
        buttons = [button for button in buttons if button is not None]
        if not buttons:
            return
        heading = tk.Menubutton(self.gui.options_bar, text=title, relief="raised")
        menu = tk.Menu(heading, tearoff=False)
        def update():
            from .actionavailability import action_reason
            self.gui.refresh_action_availability()
            for index, button in enumerate(buttons):
                menu.entryconfigure(index, state=button.cget("state"), label=button.cget("text") + (" — " + action_reason(self.gui, button) if action_reason(self.gui, button) else ""))
        menu.configure(postcommand=update)
        for button in buttons:
            menu.add_command(label=button.cget("text"), command=button.invoke)
        heading.configure(menu=menu)
        heading.pack(side="left", padx=(8, 0))
        self.menus[title] = menu

    def refresh(self):
        gui, g = self.gui, self.gui.game
        gui.refresh_action_availability()
        for button in self.buttons:
            button.place_forget()
        shown = [gui.draw_button]
        def include(name, condition=True):
            button = getattr(gui, name, None)
            if button is not None and condition:
                shown.append(button)
        hand = gui.selection.hand_index is not None
        table = gui.selection.table_index is not None
        spot = gui.selection.target_position is not None
        if hand and not table:
            include("play_button", g.enable_table or (not g.enable_discard_pile and not g.enable_interactions))
            include("discard_button", g.enable_discard_pile)
            include("play_face_down_button")
            include("personal_pile_button")
            include("flip_hand_button")
            if hasattr(self, "give_button"):
                shown.append(self.give_button)
                self.give_button.configure(state="normal" if g.active_player_indices() and not g.current_player_must_confirm_point() and not g.current_player_must_confirm_pot_withdrawal() else "disabled")
            if hasattr(gui, "special_actions_ui"):
                shown.extend(gui.special_actions_ui.buttons)
        if table:
            for name in ("take_table_button", "table_discard_button", "flip_table_card_button"):
                include(name)
            include("move_table_card_button")
        if hand and spot:
            include("play_at_spot_button")
        self.shown = list(dict.fromkeys(shown))
        self.layout()

    def layout(self):
        frame = self.gui.card_actions_frame
        if not frame.winfo_exists():
            return
        width = max(1, frame.winfo_width())
        x, y, row_height = 0, 0, 0
        for button in self.shown:
            w, h = min(button.winfo_reqwidth(), width), button.winfo_reqheight()
            if x and x + w > width:
                x, y, row_height = 0, y + row_height + 5, 0
            button.place(x=x, y=y, width=w, height=h)
            x += w + 6
            row_height = max(row_height, h)
        height = max(1, y + row_height + 3)
        if frame.winfo_reqheight() != height:
            frame.configure(height=height)
