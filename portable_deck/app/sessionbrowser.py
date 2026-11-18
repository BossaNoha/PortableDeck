"""A compact library for browsing named game sessions."""
import os
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog, ttk
import tkinter as tk
from .sessionfiles import rename_session, delete_session
from .sessioncatalog import list_sessions


class SessionBrowser:
    def __init__(self, parent, saves_dir):
        self.parent = parent
        self.base_saves_dir = saves_dir
        self.saves_dir = saves_dir
        self.selected_path = None
        self.window = tk.Toplevel(parent)
        self.window.title("Load save")
        self.window.transient(parent)
        self.window.grab_set()
        self.window.minsize(660, 360)
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)

        container = tk.Frame(self.window, padx=12, pady=12)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)
        self.source = tk.StringVar(value="saves")
        sources = tk.Frame(container)
        sources.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        for label, value in (("Saved games", "saves"), ("Autosaves", "autosaves")):
            tk.Radiobutton(sources, text=label, variable=self.source, value=value,
                           indicatoron=False, command=self.change_source).pack(side="left", padx=(0, 5))
        columns = ("name", "players", "turn", "configuration", "modified", "saved")
        self.tree = ttk.Treeview(container, columns=columns, show="headings", selectmode="browse")
        for key, title, width in (
            ("name", "Session", 180), ("players", "Players", 220),
            ("turn", "Next turn", 120), ("configuration", "Configuration", 160),
            ("modified", "Modified preset", 110), ("saved", "Saved", 145),
        ):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor="w")
        self.tree.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<Double-1>", lambda _event: self.load_selected())
        self.tree.bind("<Return>", lambda _event: self.load_selected())

        horizontal = ttk.Scrollbar(container, orient="horizontal", command=self.tree.xview)
        horizontal.grid(row=2, column=0, sticky="ew")
        self.tree.configure(xscrollcommand=horizontal.set)

        actions = tk.Frame(container)
        actions.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        tk.Button(actions, text="Load", command=self.load_selected).pack(side="left")
        tk.Button(actions, text="Rename", command=self.rename_selected).pack(side="left", padx=5)
        tk.Button(actions, text="Delete", command=self.delete_selected).pack(side="left")
        tk.Button(actions, text="Browse…", command=self.browse_external).pack(side="left", padx=5)
        tk.Button(actions, text="Cancel", command=self.window.destroy).pack(side="right")
        self.refresh()
        self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)

    def change_source(self):
        self.saves_dir = (os.path.join(self.base_saves_dir, "autosaves")
                          if self.source.get() == "autosaves" else self.base_saves_dir)
        self.refresh()

    def session_path(self, filename):
        if self.source.get() == "autosaves" and filename == "last_session.json":
            return os.path.join(self.base_saves_dir, filename)
        return os.path.join(self.saves_dir, filename)

    def refresh(self, select_name=None):
        self.tree.delete(*self.tree.get_children())
        try:
            entries = list_sessions(self.base_saves_dir, self.source.get())
        except OSError as error:
            messagebox.showerror('Could not list sessions', str(error), parent=self.window)
            return
        for entry in entries:
            names = ', '.join(entry.player_names) if entry.error is None else 'Could not read session'
            next_turn = entry.next_player or ('Unavailable' if entry.error else 'Unknown')
            saved_at = (datetime.fromtimestamp(entry.saved_at).strftime('%Y-%m-%d %H:%M')
                        if entry.saved_at is not None else 'Unavailable')
            modified = {True: 'Yes', False: 'No'}.get(entry.modified, 'Unknown')
            self.tree.insert('', 'end', iid=entry.filename, values=(entry.filename, names, next_turn,
                             entry.configuration or 'Unknown', modified, saved_at))
        if select_name and self.tree.exists(select_name):
            self.tree.selection_set(select_name)
            self.tree.focus(select_name)

    def selected_filename(self):
        selection = self.tree.selection()
        return selection[0] if selection else None

    def load_selected(self):
        filename = self.selected_filename()
        if not filename:
            messagebox.showinfo("Select a session", "Choose a saved session to load.", parent=self.window)
            return
        self.selected_path = self.session_path(filename)
        self.window.destroy()

    def rename_selected(self):
        old_name = self.selected_filename()
        if not old_name:
            messagebox.showinfo("Select a session", "Choose a session to rename.", parent=self.window)
            return
        new_name = simpledialog.askstring("Rename session", "New session name:", initialvalue=os.path.splitext(old_name)[0], parent=self.window)
        if new_name is None:
            return
        try:
            new_path = rename_session(self.session_path(old_name), new_name)
        except (OSError, TypeError, ValueError) as error:
            messagebox.showerror("Could not rename session", str(error), parent=self.window)
            return
        self.refresh(select_name=new_path.name)

    def delete_selected(self):
        filename = self.selected_filename()
        if not filename:
            messagebox.showinfo("Select a session", "Choose a session to delete.", parent=self.window)
            return
        if not messagebox.askyesno("Delete session?", f"Permanently delete '{filename}'?", parent=self.window):
            return
        try:
            delete_session(self.session_path(filename), confirmed=True)
        except (OSError, TypeError, ValueError) as error:
            messagebox.showerror("Could not delete session", str(error), parent=self.window)
            return
        self.refresh()

    def browse_external(self):
        path = filedialog.askopenfilename(
            title="Browse for a saved session",
            initialdir=self.saves_dir,
            filetypes=(("Saved games", "*.json"), ("All files", "*.*")),
            parent=self.window,
        )
        if path:
            self.selected_path = path
            self.window.destroy()

    def show(self):
        self.window.wait_window()
        return self.selected_path
