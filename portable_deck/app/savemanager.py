"""Named save management and save-name validation."""
import os
from dataclasses import asdict
from tkinter import messagebox, filedialog
from .sessionview import TableViewState
from .namedsaves import save_named_session, validate_named_save_path, next_session_number


class SaveManager:
    def __init__(self, root, saves_dir):
        self.root = root
        self.saves_dir = saves_dir
        self.table_view = TableViewState()

    def save_session(self, game):
        path = getattr(game, "named_save_path", None)
        if not path:
            return self.save_session_as(game)
        try:
            save_named_session(game, path, client_state={"table_view": asdict(self.table_view)}, overwrite=True)
            messagebox.showinfo("Game saved", f"Saved as {os.path.basename(path)}.", parent=self.root)
            return True
        except (OSError, TypeError, ValueError) as error:
            messagebox.showerror("Could not save game", str(error), parent=self.root)
            return False

    def save_session_as(self, game):
        path = filedialog.asksaveasfilename(
            title="Save as",
            initialdir=self.saves_dir,
            initialfile=f"session{self.next_session_number()}.json",
            defaultextension=".json",
            filetypes=(("Saved sessions", "*.json"), ("All files", "*.*")),
            confirmoverwrite=False,
            parent=self.root,
        )
        if not path:
            return False
        name = os.path.basename(path)
        try:
            validate_named_save_path(path)
        except (TypeError, ValueError) as error:
            messagebox.showerror("Reserved save", str(error), parent=self.root)
            return False
        existing = os.path.exists(path)
        if existing and not messagebox.askyesno(
            "Replace save?",
            f"A save named '{name}' already exists. Replace it?",
            parent=self.root,
        ):
            return False
        try:
            save_named_session(game, path, client_state={"table_view": asdict(self.table_view)}, overwrite=existing)
            messagebox.showinfo("Game saved", f"Saved as {name}.", parent=self.root)
            return True
        except (OSError, TypeError, ValueError) as error:
            messagebox.showerror("Could not save game", str(error), parent=self.root)
            return False

    def next_session_number(self):
        return next_session_number(self.saves_dir)
