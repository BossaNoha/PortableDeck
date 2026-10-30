"""Named save management and save-name validation."""
import os
import re
from tkinter import messagebox, simpledialog


class SaveManager:
    def __init__(self, root, saves_dir):
        self.root = root
        self.saves_dir = saves_dir

    def save_session(self, game):
        name = simpledialog.askstring(
            "Save game",
            "Save name:",
            initialvalue=f"session{self.next_session_number()}",
            parent=self.root,
        )
        if name is None:
            return False
        name = name.strip()
        if (
            not name
            or name in {".", ".."}
            or os.path.basename(name) != name
            or re.search(r'[<>:"/\\|?*]', name)
        ):
            messagebox.showerror(
                "Invalid name",
                "Enter a file name without a folder path or special characters.",
                parent=self.root,
            )
            return False
        if not name.lower().endswith(".json"):
            name += ".json"
        path = os.path.join(self.saves_dir, name)
        if os.path.exists(path) and not messagebox.askyesno(
            "Replace save?",
            f"A save named '{name}' already exists. Replace it?",
            parent=self.root,
        ):
            return False
        try:
            game.save_session(path)
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
