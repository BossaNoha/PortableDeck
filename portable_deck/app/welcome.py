"""A one-time introduction stored locally for this device's user account."""
import os
from pathlib import Path
import tkinter as tk

INTRO_TEXT = (
    "Portable Deck brings a physical deck of cards to your screen. It is a virtual "
    "tabletop where you can play the card games you already know, revisit old "
    "favourites, or make up something entirely your own.\n\n"
    "Just like a real deck, it is not tied to one particular game. Shape the "
    "experience through the settings to suit the rules you want to play by. "
    "You and your fellow players bring the rules and decisions; Portable Deck "
    "provides the cards and a shared space to play.\n\n"
    "Think of it as opening a box of cards rather than choosing a single game. "
    "Set up your table, gather your players, and make it your own."
)


def welcome_marker():
    if os.name == "nt":
        folder = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        folder = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return folder / "PortableDeck" / "welcome_seen"


def show_first_run_intro(parent, marker=None):
    marker = Path(marker) if marker is not None else welcome_marker()
    if marker.is_file() or not parent.winfo_exists():
        return None
    window = tk.Toplevel(parent)
    window.withdraw()
    window.title("Welcome to Portable Deck")
    window.transient(parent)
    window.resizable(False, False)
    width = min(540, parent.winfo_screenwidth() - 60)
    body = tk.Frame(window, padx=24, pady=22)
    body.pack(fill="both", expand=True)
    tk.Label(body, text="Your cards. Your rules.", font=("TkDefaultFont", 18, "bold"),
             wraplength=width - 48, justify="left").pack(anchor="w", pady=(0, 16))
    tk.Label(body, text=INTRO_TEXT, wraplength=width - 48, justify="left",
             anchor="w").pack(fill="x")

    def dismiss():
        try:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text("Welcome acknowledged.\n", encoding="utf-8")
        except OSError:
            # A read-only user-data directory must not prevent starting the app.
            pass
        window.destroy()

    button = tk.Button(body, text="Let's begin", command=dismiss, padx=14, pady=4)
    button.pack(anchor="e", pady=(20, 0))
    window.protocol("WM_DELETE_WINDOW", dismiss)
    window.update_idletasks()
    height = window.winfo_reqheight()
    x = max(0, min(parent.winfo_rootx() + (parent.winfo_width() - width) // 2,
                   parent.winfo_screenwidth() - width - 20))
    y = max(0, min(parent.winfo_rooty() + (parent.winfo_height() - height) // 2,
                   parent.winfo_screenheight() - height - 60))
    window.geometry(f"{width}x{height}+{x}+{y}")
    window.deiconify()
    window.grab_set()
    button.focus_set()
    window.bind("<Return>", lambda _: dismiss())
    window.bind("<Escape>", lambda _: dismiss())
    return window
