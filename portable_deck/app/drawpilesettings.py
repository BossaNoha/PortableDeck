"""Initial draw-pile distribution controls; validation stays in the core."""
import tkinter as tk
from tkinter import ttk
from ..ui.contentscrollarea import ContentScrollArea


class DrawPileSettings:
    def __init__(self, parent, settings, players_var=None):
        self.players_var = players_var if players_var is not None else tk.IntVar(value=settings.get("num_players", 3))
        self.enabled = tk.BooleanVar(value=settings.get("enable_draw_pile_setup", False))
        self.rows = []
        tk.Checkbutton(parent, text="Enable additional draw piles", variable=self.enabled, command=self.update).pack(anchor="w")
        self.body = tk.Frame(parent)
        tk.Label(self.body, text="One card set: starting hands are dealt first, then these piles receive their cards. The remainder stays in main.",
                 wraplength=310, justify="left").pack(anchor="w", pady=5)
        self.scroll_area = ContentScrollArea(self.body, width=310)
        self.scroll_area.pack(fill="both", expand=True)
        self.entries = self.scroll_area.contents
        tk.Button(self.body, text="Add draw pile", command=self.add).pack(anchor="w", pady=5)
        for entry in settings.get("draw_pile_setup", []):
            self.add(entry)
        self.players_var.trace_add("write", self.update_owners)
        self.update()

    def update(self):
        if self.enabled.get(): self.body.pack(fill="x")
        else: self.body.pack_forget()

    def update_owners(self, *_):
        try: count = int(self.players_var.get())
        except (ValueError, tk.TclError): return
        for row in self.rows:
            row["owner_input"].configure(values=["Shared"] + [f"Player {i + 1}" for i in range(count)])

    def add(self, entry=None):
        if entry is None:
            number = 1
            used = {row["id"].get() for row in self.rows}
            while f"pile-{number}" in used: number += 1
            entry = {"id": f"pile-{number}", "name": f"Draw pile {number}", "owner": None, "count": 0}
        frame = tk.LabelFrame(self.entries, text="Draw pile", padx=5, pady=4)
        frame.pack(fill="x", pady=4)
        row = {key: tk.StringVar(value=str(entry[key])) for key in ("id", "name", "count")}
        row["owner"] = tk.StringVar(value="Shared" if entry["owner"] is None else f"Player {entry['owner'] + 1}")
        for index, (key, label) in enumerate((("id", "Stable ID"), ("name", "Name"), ("owner", "Owner"), ("count", "Initial cards"))):
            tk.Label(frame, text=label).grid(row=index, column=0, sticky="w")
            if key == "owner":
                widget = ttk.Combobox(frame, state="readonly", textvariable=row[key], width=20)
                row["owner_input"] = widget
            elif key == "count":
                widget = tk.Spinbox(frame, from_=0, to=100000, textvariable=row[key], width=20)
            else:
                widget = tk.Entry(frame, textvariable=row[key], width=23)
            widget.grid(row=index, column=1, sticky="ew")
        def remove():
            self.rows.remove(row)
            frame.destroy()
            self.scroll_area.schedule_resize()
        tk.Button(frame, text="Remove", command=remove).grid(row=4, column=1, sticky="e", pady=3)
        self.rows.append(row)
        self.update_owners()
        self.scroll_area.schedule_resize()

    def values(self):
        entries = []
        for row in self.rows:
            owner = row["owner"].get()
            entries.append({"id": row["id"].get(), "name": row["name"].get(),
                            "owner": None if owner == "Shared" else int(owner.removeprefix("Player ")) - 1,
                            "count": int(row["count"].get())})
        return {"enable_draw_pile_setup": self.enabled.get(), "draw_pile_setup": entries}
