"""Named save management and save-name validation."""
import os
import re
from tkinter import messagebox, filedialog


class SaveManager:
    def __init__(self, root, saves_dir):
        self.root = root
        self.saves_dir = saves_dir

    def save_session(self, game):
        path = getattr(game, "named_save_path", None)
        if not path:
            return self.save_session_as(game)
        try:
            game.save_session(path)
            messagebox.showinfo("Game saved", f"Saved as {os.path.basename(path)}.", parent=self.root)
            return True
        except (OSError, TypeError, ValueError) as error:
            messagebox.showerror("Could not save game", str(error), parent=self.root)
            return False

    def save_session_as(self, game):
        os.makedirs(self.saves_dir, exist_ok=True)
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
        if name.lower() == "last_session.json" or os.path.basename(os.path.dirname(os.path.abspath(path))).lower() == "autosaves":
            messagebox.showerror("Reserved save", "Choose a named session outside the automatic checkpoint files.", parent=self.root)
            return False
        if os.path.exists(path) and not messagebox.askyesno(
            "Replace save?",
            f"A save named '{name}' already exists. Replace it?",
            parent=self.root,
        ):
            return False
        try:
            game.save_session(path)
            game.named_save_path = path
            messagebox.showinfo("Game saved", f"Saved as {name}.", parent=self.root)
            return True
        except (OSError, TypeError, ValueError) as error:
            messagebox.showerror("Could not save game", str(error), parent=self.root)
            return False

    def next_session_number(self):
        numbers = []
        for filename in os.listdir(self.saves_dir):
            match = re.fullmatch(r"session(\d+)\.json", filename, re.IGNORECASE)
            if match:
                numbers.append(int(match.group(1)))
        return max(numbers, default=0) + 1
