"""Browse, select, edit, and duplicate deck files."""
import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..core.deck import Deck
from .deckbuilder import DeckBuilder
from .deckpreview import show_deck_preview


class DeckLibrary:
    def __init__(self, parent, decks_dir, on_use):
        self.parent = parent
        self.decks_dir = decks_dir
        self.on_use = on_use
        self.window = tk.Toplevel(parent)
        self.window.title("Deck library")
        self.window.transient(parent)
        self.window.grab_set()
        self.window.geometry("760x390")
        self.window.minsize(560, 300)
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)

        container = tk.Frame(self.window, padx=12, pady=12)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(
            container, columns=("name", "count", "symbols"),
            show="headings", selectmode="browse",
        )
        for key, title, width in (
            ("name", "Deck", 190), ("count", "Cards", 75), ("symbols", "Symbols", 420),
        ):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<Double-1>", lambda _event: self.use_selected())
        self.tree.bind("<Return>", lambda _event: self.use_selected())

        actions = tk.Frame(container)
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        tk.Button(actions, text="Use selected", command=self.use_selected).pack(side="left")
        tk.Button(actions, text="Preview", command=self.preview_selected).pack(side="left", padx=(5, 0))
        tk.Button(actions, text="Edit…", command=self.edit_selected).pack(side="left", padx=5)
        tk.Button(actions, text="Duplicate…", command=self.duplicate_selected).pack(side="left")
        tk.Button(actions, text="Import…", command=self.import_deck).pack(side="left", padx=(5, 0))
        tk.Button(actions, text="Export…", command=self.export_selected).pack(side="left", padx=5)
        tk.Button(actions, text="Refresh", command=self.refresh).pack(side="left", padx=5)
        tk.Button(actions, text="Close", command=self.window.destroy).pack(side="right")
        self.refresh()
        self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)

    def refresh(self, select_path=None):
        self.tree.delete(*self.tree.get_children())
        os.makedirs(self.decks_dir, exist_ok=True)
        names = sorted(
            (name for name in os.listdir(self.decks_dir) if name.lower().endswith(".json")),
            key=str.casefold,
        )
        for filename in names:
            path = os.path.join(self.decks_dir, filename)
            try:
                deck = Deck(path)
                count = str(len(deck.flat_deck))
                symbols = ", ".join(deck.types)
            except (OSError, ValueError, KeyError, TypeError):
                count, symbols = "Invalid", "Could not read this deck"
            self.tree.insert("", "end", iid=filename, values=(os.path.splitext(filename)[0], count, symbols))
        if select_path:
            filename = os.path.basename(select_path)
            if self.tree.exists(filename):
                self.tree.selection_set(filename)
                self.tree.focus(filename)

    def selected_path(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Select a deck", "Choose a deck from the list first.", parent=self.window)
            return None
        return os.path.join(self.decks_dir, selection[0])

    def use_selected(self):
        path = self.selected_path()
        if path:
            try:
                Deck(path)
            except (OSError, ValueError, KeyError, TypeError) as error:
                messagebox.showerror("Invalid deck", str(error), parent=self.window)
                return
            self.on_use(path)
            self.window.destroy()

    def edit_selected(self):
        path = self.selected_path()
        if not path:
            return
        try:
            Deck(path)
        except (OSError, ValueError, KeyError, TypeError) as error:
            messagebox.showerror("Cannot edit deck", str(error), parent=self.window)
            return
        DeckBuilder(
            self.window, path, self.decks_dir,
            lambda updated: (self.on_use(updated), self.refresh(select_path=updated)),
            edit_path=path,
        )

    def preview_selected(self):
        path = self.selected_path()
        if path:
            show_deck_preview(self.window, path)

    def duplicate_selected(self):
        path = self.selected_path()
        if not path:
            return
        try:
            Deck(path)
        except (OSError, ValueError, KeyError, TypeError) as error:
            messagebox.showerror("Cannot duplicate deck", str(error), parent=self.window)
            return
        DeckBuilder(
            self.window, path, self.decks_dir,
            lambda created: (self.on_use(created), self.refresh(select_path=created)),
        )

    def import_deck(self):
        source = filedialog.askopenfilename(
            title="Import a deck", initialdir=self.decks_dir,
            filetypes=(("JSON deck", "*.json"), ("All files", "*.*")), parent=self.window,
        )
        if not source:
            return
        try:
            Deck(source)
        except (OSError, ValueError, KeyError, TypeError) as error:
            messagebox.showerror("Invalid deck", str(error), parent=self.window)
            return
        filename = os.path.basename(source)
        if not filename.lower().endswith(".json"):
            filename += ".json"
        target = os.path.join(self.decks_dir, filename)
        if os.path.normcase(os.path.abspath(source)) == os.path.normcase(os.path.abspath(target)):
            messagebox.showinfo("Already in library", "This deck is already in the deck library.", parent=self.window)
            return
        if os.path.exists(target) and not messagebox.askyesno(
            "Replace deck?", f"A deck named '{os.path.basename(target)}' already exists. Replace it?",
            parent=self.window,
        ):
            return
        try:
            shutil.copy2(source, target)
        except OSError as error:
            messagebox.showerror("Could not import deck", str(error), parent=self.window)
            return
        self.on_use(target)
        self.refresh(select_path=target)

    def export_selected(self):
        source = self.selected_path()
        if not source:
            return
        try:
            Deck(source)
        except (OSError, ValueError, KeyError, TypeError) as error:
            messagebox.showerror("Invalid deck", str(error), parent=self.window)
            return
        target = filedialog.asksaveasfilename(
            title="Export deck", initialfile=os.path.basename(source),
            defaultextension=".json", filetypes=(("JSON deck", "*.json"),), parent=self.window,
        )
        if not target:
            return
        if not target.lower().endswith(".json"):
            target += ".json"
        if os.path.normcase(os.path.abspath(source)) == os.path.normcase(os.path.abspath(target)):
            messagebox.showinfo("Already exported", "Choose a location outside the deck library.", parent=self.window)
            return
        try:
            shutil.copy2(source, target)
        except OSError as error:
            messagebox.showerror("Could not export deck", str(error), parent=self.window)
            return
        messagebox.showinfo("Deck exported", f"Exported to:\n{target}", parent=self.window)

    def show(self):
        self.window.wait_window()
