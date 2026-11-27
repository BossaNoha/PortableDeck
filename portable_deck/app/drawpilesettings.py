"""Initial draw-pile distribution controls; validation stays in the core."""
import tkinter as tk
from tkinter import ttk
from ..ui.contentscrollarea import ContentScrollArea


class DrawPileSettings:
    def __init__(self, parent, settings, players_var=None):
        self.players_var = players_var if players_var is not None else tk.IntVar(value=settings.get("num_players", 3))
        self.enabled = tk.BooleanVar(value=settings.get("enable_draw_pile_setup", False))
        self.linked = tk.BooleanVar(value=settings.get("enable_linked_recycling", False))
        self.saved_links = settings.get("draw_pile_recycling", {})
        self.rows = []
        self.hand_mode = tk.BooleanVar(value=settings.get("deal_starting_hands_from_piles", False))
        self.hand_vars = [tk.StringVar(value=value) for value in settings.get("initial_hand_sources", [])]
        self.hand_frame = tk.LabelFrame(parent, text="Starting hand sources")
        self.hand_widgets = []
        tk.Checkbutton(parent, text="Deal starting hands from selected draw piles", variable=self.hand_mode, command=self.update).pack(anchor="w")
        tk.Label(self.hand_frame, text="Piles are filled first. Initial counts include cards subsequently dealt into hands.", wraplength=300, justify="left").pack(anchor="w")
        tk.Checkbutton(parent, text="Enable linked recycling (assigned discard only)", variable=self.linked, command=self.update).pack(anchor="w")
        self.main_frame = tk.LabelFrame(parent, text="Main draw pile recycling", padx=4, pady=4)
        self.main_link = self.link_controls(self.main_frame, self.saved_links.get("main"), shared_only=True)
        self.main_link["frame"].pack(fill="x")
        tk.Label(self.main_frame, text="Enable manual recycling in Discard pile. Personal links require an owned draw pile and use that owner's discard.",
                 wraplength=300, justify="left").pack(anchor="w", pady=4)
        tk.Checkbutton(parent, text="Enable additional draw piles", variable=self.enabled, command=self.update).pack(anchor="w")
        self.body = tk.Frame(parent)
        tk.Label(self.body, text="One card set. Normally hands are dealt first; selected-source mode fills piles first. The remainder stays in main.",
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
        if self.hand_mode.get(): self.hand_frame.pack(fill="x", pady=4)
        else: self.hand_frame.pack_forget()
        self.update_hand_sources()
        if self.linked.get(): self.main_frame.pack(fill="x", pady=4)
        else: self.main_frame.pack_forget()
        for row in self.rows:
            if self.linked.get(): row["link"]["frame"].grid()
            else: row["link"]["frame"].grid_remove()
        if self.enabled.get(): self.body.pack(fill="x")
        else: self.body.pack_forget()

    def link_controls(self, parent, link=None, shared_only=False):
        frame = tk.Frame(parent)
        kind = tk.StringVar(value="None" if link is None else "Personal discard" if link["personal"] else "Shared discard")
        index = tk.StringVar(value=str(link["pile_index"] + 1 if link else 1))
        tk.Label(frame, text="Recycle from:").pack(anchor="w")
        ttk.Combobox(frame, state="readonly", textvariable=kind, width=20,
                     values=["None", "Shared discard"] + ([] if shared_only else ["Personal discard"])).pack(side="left")
        tk.Spinbox(frame, from_=1, to=20, textvariable=index, width=4).pack(side="left", padx=4)
        automatic = tk.BooleanVar(value=link.get("automatic", False) if link else False)
        tk.Checkbutton(frame, text="Automatically refill when drawing", variable=automatic).pack(anchor="w")
        return {"frame": frame, "kind": kind, "index": index, "automatic": automatic}

    def update_owners(self, *_):
        try: count = int(self.players_var.get())
        except (ValueError, tk.TclError): return
        for row in self.rows:
            row["owner_input"].configure(values=["Shared"] + [f"Player {i + 1}" for i in range(count)])
        self.update_hand_sources()

    def update_hand_sources(self):
        try: count = int(self.players_var.get())
        except (ValueError, tk.TclError): return
        while len(self.hand_vars) < count:
            self.hand_vars.append(tk.StringVar(value="main"))
        while len(self.hand_widgets) < count:
            index = len(self.hand_widgets)
            row = tk.Frame(self.hand_frame)
            tk.Label(row, text=f"Player {index + 1}").pack(side="left")
            choice = ttk.Combobox(row, state="readonly", width=19, textvariable=self.hand_vars[index], postcommand=self.update_hand_sources)
            choice.pack(side="left", padx=4)
            self.hand_widgets.append((row, choice))
        for index, (row, choice) in enumerate(self.hand_widgets):
            if index >= count:
                row.pack_forget()
                continue
            row.pack(anchor="w", pady=2)
            values = ["main"]
            if self.enabled.get():
                values.extend(entry["id"].get() for entry in self.rows if entry["owner"].get() in ("Shared", f"Player {index + 1}"))
            choice.configure(values=values)

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
        row["link"] = self.link_controls(frame, self.saved_links.get(entry["id"]))
        row["link"]["frame"].grid(row=4, column=0, columnspan=2, sticky="ew", pady=3)
        tk.Button(frame, text="Remove", command=remove).grid(row=5, column=1, sticky="e", pady=3)
        self.rows.append(row)
        self.update_owners()
        self.update()
        self.scroll_area.schedule_resize()

    def values(self):
        entries = []
        links = {}
        def add_link(pile_id, controls):
            kind = controls["kind"].get()
            if kind != "None":
                links[pile_id] = {"personal": kind == "Personal discard", "pile_index": int(controls["index"].get()) - 1}
                if controls["automatic"].get():
                    links[pile_id]["automatic"] = True
        add_link("main", self.main_link)
        for row in self.rows:
            add_link(row["id"].get(), row["link"])
            owner = row["owner"].get()
            entries.append({"id": row["id"].get(), "name": row["name"].get(),
                            "owner": None if owner == "Shared" else int(owner.removeprefix("Player ")) - 1,
                            "count": int(row["count"].get())})
        return {"enable_draw_pile_setup": self.enabled.get(), "draw_pile_setup": entries,
                "enable_linked_recycling": self.linked.get(), "draw_pile_recycling": links,
                "deal_starting_hands_from_piles": self.hand_mode.get(),
                "initial_hand_sources": [value.get() for value in self.hand_vars[:int(self.players_var.get())]]}
