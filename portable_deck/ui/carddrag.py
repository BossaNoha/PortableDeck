"""Drag cards to empty table slots using existing game actions."""
import tkinter as tk
from time import monotonic
from .cardactions import play_selected, play_at_selected_spot, move_selected_table_card
from ..core.actionavailability import drop_availability

class CardDrag:
    def __init__(self, gui):
        self.gui = gui
        self.last_scroll_at = 0.0
        self.pending = None
        self.dragging = False
        self.suppress_release = False
        self.highlight = None
        self.hint = tk.Label(gui.options_bar, text="Drop on the table; Esc cancels")
        self.escape_binding = gui.root.bind("<Escape>", self.cancel, add="+")
        gui.layout_frame.bind("<Destroy>", self.cleanup, add="+")

    def bind(self, widget, source, index):
        widget.bind("<ButtonPress-1>", lambda event: self.press(event, source, index))
        widget.bind("<B1-Motion>", self.motion)
        widget.bind("<ButtonRelease-1>", self.release)

    def press(self, event, source, index):
        self.pending = (source, index, event.x_root, event.y_root)
        self.dragging = False
        self.last_scroll_at = 0.0

    def target(self, x, y):
        widget = self.gui.root.winfo_containing(x, y)
        game = self.gui.game
        automatic = (self.pending is not None and self.pending[0] == "hand"
                     and not game.allow_positioned_play and not game.allow_play_in_front_of_players)
        while widget is not None:
            if automatic and widget is self.gui.table_frame:
                return self.gui.table_frame.canvas
            if not automatic and hasattr(widget, "_table_drop_position"):
                return widget
            widget = widget.master
        return None

    def motion(self, event):
        if self.pending is None:
            return
        source, index, x, y = self.pending
        if not self.dragging and abs(event.x_root-x) + abs(event.y_root-y) < 8:
            return
        self.dragging = True
        self.hint.pack(side="right", padx=8)
        target = self.target(event.x_root, event.y_root)
        if target is not None and not drop_availability(
                self.gui.game, source, index, getattr(target, "_table_drop_position", None)).availability.allowed:
            target = None
        if target != (self.highlight[0] if self.highlight else None):
            self.clear_highlight()
            if target is not None:
                self.highlight = (target, target.cget("background"))
                target.configure(background="#c7e9c0")
        canvas = self.gui.table_frame.canvas
        cx, cy = event.x_root-canvas.winfo_rootx(), event.y_root-canvas.winfo_rooty()
        if (0 <= cx <= canvas.winfo_width() and 0 <= cy <= canvas.winfo_height()
                and monotonic() - self.last_scroll_at >= 0.06):
            dx = -1 if cx < 20 else 1 if cx > canvas.winfo_width()-20 else 0
            dy = -1 if cy < 20 else 1 if cy > canvas.winfo_height()-20 else 0
            if dx or dy:
                self.last_scroll_at = monotonic()
                # Small pixel steps, independent of mouse-event frequency.
                bounds = canvas.bbox("all")
                if bounds:
                    if dx:
                        canvas.xview_moveto(canvas.xview()[0] + dx * 12 / max(1, bounds[2] - bounds[0]))
                    if dy:
                        canvas.yview_moveto(canvas.yview()[0] + dy * 12 / max(1, bounds[3] - bounds[1]))
        return "break"

    def clear_highlight(self):
        if self.highlight:
            widget, color = self.highlight
            if widget.winfo_exists():
                widget.configure(background=color)
        self.highlight = None

    def cancel(self, event=None):
        was_dragging = self.dragging
        if event is not None and was_dragging:
            self.suppress_release = True
        self.pending = None
        self.dragging = False
        self.clear_highlight()
        self.hint.pack_forget()
        return "break" if was_dragging else None

    def release(self, event):
        if self.suppress_release:
            self.suppress_release = False
            return "break"
        pending, dragging = self.pending, self.dragging
        target = self.target(event.x_root, event.y_root) if dragging else None
        position = getattr(target, "_table_drop_position", None)
        self.cancel()
        if not dragging:
            return
        # Reset Tk's pressed-button state before rebuilding any card widgets.
        if event.widget.winfo_exists():
            event.widget.configure(relief="raised")
        if pending is not None and target is not None:
            self.drop(pending[0], pending[1], position)
        return "break"

    def drop(self, source, index, position=None):
        gui, game = self.gui, self.gui.game
        proposal = drop_availability(game, source, index, position)
        if not proposal.availability.allowed:
            return False
        if source == "hand":
            gui.selection.hand_index = index
            gui.selection.table_index = None
            gui.selection.target_position = proposal.target_position
            action = play_at_selected_spot if proposal.action == "play_at_position" else play_selected
            gui.run_action(action, game, gui.hand_frame, gui.table_frame, gui.render_log, gui.status_panel)
        elif source == "table":
            gui.selection.table_index = index
            gui.selection.target_position = proposal.target_position
            gui.run_action(move_selected_table_card, game, gui.table_frame, gui.render_log, gui.status_panel)
        else:
            return False
        return True

    def cleanup(self, event):
        if event.widget == self.gui.layout_frame:
            self.cancel()
            self.gui.root.unbind("<Escape>", self.escape_binding)
