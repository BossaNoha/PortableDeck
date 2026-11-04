"""Scrollable visual preview for a card deck."""
import os
import tkinter as tk
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
        wraplength=480,
        justify="left",
    ).pack(anchor="w", pady=(0, 8))

    table = tk.LabelFrame(window, text="Table", padx=8, pady=5)
    table.pack(fill="both", expand=True, padx=12, pady=(0, 8))
    canvas = tk.Canvas(table, highlightthickness=0)
    cards_frame = tk.Frame(canvas)
    frame_id = canvas.create_window((0, 0), window=cards_frame, anchor="nw")
    cards = []
    for type_name, values in zip(deck.types, deck.cards):
        for value in sorted(values, key=_card_sort_key):
            cards.append(tk.Button(
                cards_frame,
                text=f"{value}\n{type_name}",
                width=18,
                wraplength=150,
                command=lambda: None,
            ))
    scrollbar = tk.Scrollbar(table, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    tk.Button(window, text="Close", command=window.destroy).pack(
        anchor="e", padx=12, pady=(0, 10)
    )

    window.update_idletasks()
    # Measure the actual widgets: font sizes and Windows display scaling vary.
    card_width = max(card.winfo_reqwidth() for card in cards) + 6
    previous_columns = 0

    def update_scroll_region(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
        overflowing = cards_frame.winfo_reqheight() > canvas.winfo_height()
        if overflowing and not scrollbar.winfo_manager():
            scrollbar.pack(side="right", fill="y", before=canvas)
        elif not overflowing and scrollbar.winfo_manager():
            scrollbar.pack_forget()
            canvas.yview_moveto(0)

    def arrange_cards(event):
        nonlocal previous_columns
        canvas.itemconfigure(frame_id, width=event.width)
        columns = max(1, event.width // card_width)
        if columns != previous_columns:
            for column in range(max(columns, previous_columns)):
                cards_frame.grid_columnconfigure(column, weight=0, minsize=0)
            for index, card in enumerate(cards):
                card.grid(row=index // columns, column=index % columns,
                          padx=3, pady=3, sticky="nsew")
            for column in range(columns):
                cards_frame.grid_columnconfigure(column, weight=1)
            previous_columns = columns
        canvas.after_idle(update_scroll_region)

    def scroll_cards(event):
        if scrollbar.winfo_manager():
            steps = -int(event.delta / 120) if event.delta else 0
            if not steps and event.delta:
                steps = -1 if event.delta > 0 else 1
            canvas.yview_scroll(steps, "units")

    # Toplevel binding also receives events over the individual card buttons.
    window.bind("<MouseWheel>", scroll_cards)
    cards_frame.bind("<Configure>", update_scroll_region)
    canvas.bind("<Configure>", arrange_cards)

    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    columns = min(10, len(cards), max(1, (screen_width - 140) // card_width))
    canvas.configure(width=columns * card_width)
    # Lay out once at the intended width before measuring the content height.
    for index, card in enumerate(cards):
        card.grid(row=index // columns, column=index % columns,
                  padx=3, pady=3, sticky="nsew")
    window.update_idletasks()
    canvas.configure(height=cards_frame.winfo_reqheight())
    window.update_idletasks()
    width = min(window.winfo_reqwidth(), screen_width - 80)
    height = min(window.winfo_reqheight(), screen_height - 100)
    window.minsize(min(width, max(320, card_width + 70)), min(height, 200))
    window.geometry(f"{width}x{height}")



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
