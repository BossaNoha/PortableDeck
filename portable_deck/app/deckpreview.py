"""Scrollable visual preview for a card deck."""
import os
import math
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox

from ..core.deck import Deck


def show_deck_preview(parent, path):
    if isinstance(path, Deck):
        deck = path
        title = os.path.basename(deck.path)
    elif not path:
        messagebox.showinfo("Choose a deck", "Select a deck file first.", parent=parent)
        return
    else:
        try:
            deck = Deck(path)
            title = os.path.basename(path)
        except (OSError, ValueError, KeyError, TypeError) as error:
            messagebox.showerror("Could not preview deck", str(error), parent=parent)
            return

    window = tk.Toplevel(parent)
    window.title(f"Deck preview — {title}")
    window.transient(parent)
    window.minsize(560, 320)
    tk.Label(
        window,
        text=f"{title}  •  {Deck.validate_data({'types': deck.types, 'cards': deck.cards})} cards  •  {len(deck.types)} symbols",
        font=("TkDefaultFont", 12, "bold"),
        padx=12,
        pady=10,
    ).pack(anchor="w")
    tk.Label(
        window,
        text="Symbols follow the deck order; cards are sorted by value within each symbol.",
        padx=12,
    ).pack(anchor="w", pady=(0, 8))

    table = tk.LabelFrame(window, text="Table", padx=8, pady=5)
    table.pack(fill="both", expand=True, padx=12, pady=(0, 8))
    canvas = tk.Canvas(table, highlightthickness=0)
    cards_frame = tk.Frame(canvas)
    frame_id = canvas.create_window((0, 0), window=cards_frame, anchor="nw")
    cards_frame.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
    cards = []
    for type_name, values in zip(deck.types, deck.cards):
        for value in sorted(values, key=_card_sort_key):
            cards.append(tk.Button(
                cards_frame,
                text=f"{value}\n{type_name}",
                width=18,
                command=lambda: None,
            ))
    scrollbar = tk.Scrollbar(table, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    card_width = tkfont.nametofont("TkDefaultFont").measure("0" * 18) + 28

    def arrange_cards(event):
        canvas.itemconfigure(frame_id, width=event.width)
        columns = max(1, min(10, (event.width - 12) // card_width))
        for index, card in enumerate(cards):
            card.grid(row=index // columns, column=index % columns, padx=3, pady=3, sticky="nsew")
        for column in range(10):
            cards_frame.grid_columnconfigure(column, weight=1 if column < columns else 0)

    canvas.bind("<Configure>", arrange_cards)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(fill="both", expand=True)

    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    width = min(max(620, card_width * 10 + 70), screen_width - 80)
    columns = max(1, min(10, (width - 70) // card_width))
    rows = max(1, math.ceil(len(cards) / columns))
    height = min(max(320, 160 + rows * 72), screen_height - 100)
    window.geometry(f"{width}x{height}")
    tk.Button(window, text="Close", command=window.destroy).pack(anchor="e", padx=12, pady=(0, 10))


def _card_sort_key(value):
    """Sort numeric ranks first, then common face-card names, then other values."""
    text = str(value).strip()
    face_values = {
        "j": 11, "jack": 11, "knight": 11,
        "q": 12, "queen": 12,
        "k": 13, "king": 13,
        "a": 14, "ace": 14,
    }
    lowered = text.casefold()
    try:
        return 0, float(text)
    except ValueError:
        if lowered in face_values:
            return 1, face_values[lowered]
        return 2, lowered
