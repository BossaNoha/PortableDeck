"""Per-player, per-pile access and ordering preferences."""
import tkinter as tk
from ..ui.contentscrollarea import ContentScrollArea


class PersonalPileSettings:
    def __init__(self, parent, settings, players_var, fit_window, player_name=None):
        self.player_name = player_name or (lambda owner: (
            settings["player_names"][owner] if settings.get("use_custom_player_names")
            and owner < len(settings.get("player_names", [])) else f"Player {owner + 1}"
        ))
        self.parent = parent
        self.players_var = players_var
        self.fit_window = fit_window
        legacy_count = settings.get("personal_discard_pile_count", 0)
        self.enabled_var = tk.BooleanVar(value=settings.get("enable_personal_piles", legacy_count > 0))
        self.count_var = tk.StringVar(value=str(settings.get("personal_pile_count", legacy_count or 1)))
        self.saved = settings.get("personal_pile_settings", [])
        self.unequal_var = tk.BooleanVar(value=settings.get("unequal_personal_piles", False))
        self.saved_counts = settings.get("personal_pile_counts", [])
        self.owner_count_vars = []
        self.owner_labels = []
        self.syncing_counts = False
        self.rows = {}
        self.cache = {}
        tk.Checkbutton(parent, text="Enable personal piles", variable=self.enabled_var,
                       command=self.update_states).pack(anchor="w")
        self.options = tk.Frame(parent)
        self.options.pack(fill="x")
        tk.Checkbutton(self.options, text="Unequal amount of personal piles",
                       variable=self.unequal_var, command=self.rebuild).pack(anchor="w")
        count_row = tk.Frame(self.options)
        count_row.pack(anchor="w")
        tk.Label(count_row, text="Personal piles per player:").pack(side="left")
        self.shared_count = tk.Spinbox(count_row, from_=1, to=20, width=5, textvariable=self.count_var)
        self.shared_count.pack(side="left", padx=6)
        tk.Label(self.options, text="Team access currently allows only the owner.",
                 fg="#666666").pack(anchor="w", pady=4)
        self.scroll_area = ContentScrollArea(self.options, fit_window=fit_window)
        self.scroll_area.pack(fill="both", expand=True)
        self.canvas = self.scroll_area.canvas
        self.contents = self.scroll_area.contents
        self.owner_counts_frame = tk.Frame(self.contents)
        self.owner_counts_frame.pack(fill="x")
        self.pile_contents = tk.Frame(self.contents)
        self.pile_contents.pack(fill="x")
        self.count_var.trace_add("write", self.rebuild)
        players_var.trace_add("write", self.rebuild)
        self.rebuild()

    def update_names(self):
        for owner, label in enumerate(self.owner_labels):
            label.configure(text=f"{self.player_name(owner)} — piles:")
        for (owner, pile), row in self.rows.items():
            row["frame"].configure(text=f"{self.player_name(owner)} — Pile {pile + 1}")

    def row_value(self, row):
        ordering = row["ordering"].get()
        return {"access": row["access"].get(), "ordered": ordering != "Not ordered",
                "order_by": "size" if ordering == "Ordered by size" else "time",
                "new_card": row["new_card"].get(), "size_order": row["size_order"].get()}

    def sync_owner_counts(self, players, default_count):
        if len(self.owner_labels) == players:
            return
        self.syncing_counts = True
        for widget in self.owner_counts_frame.winfo_children():
            widget.destroy()
        self.owner_labels = []
        while len(self.owner_count_vars) < players:
            owner = len(self.owner_count_vars)
            value = self.saved_counts[owner] if owner < len(self.saved_counts) else default_count
            var = tk.StringVar(value=str(value))
            var.trace_add("write", self.rebuild)
            self.owner_count_vars.append(var)
        for owner in range(players):
            label = tk.Label(self.owner_counts_frame, text=f"{self.player_name(owner)} — piles:")
            label.grid(row=owner, column=0, sticky="w")
            self.owner_labels.append(label)
            tk.Spinbox(self.owner_counts_frame, from_=0, to=20, width=5,
                       textvariable=self.owner_count_vars[owner]).grid(row=owner, column=1, sticky="w", padx=6)

        self.syncing_counts = False

    def counts(self):
        count, players = int(self.count_var.get()), int(self.players_var.get())
        if not 1 <= count <= 20 or not 1 <= players <= 20:
            raise ValueError("Personal pile count must be between 1 and 20.")
        self.sync_owner_counts(players, count)
        counts = ([int(var.get()) for var in self.owner_count_vars[:players]]
                  if self.unequal_var.get() else [count] * players)
        if any(not 0 <= value <= 20 for value in counts):
            raise ValueError("Each player's pile count must be between 0 and 20.")
        return counts

    def rebuild(self, *_):
        if self.syncing_counts:
            return
        try:
            counts = self.counts()
        except ValueError:
            return
        self.cache.update({key: self.row_value(row) for key, row in self.rows.items()})
        for widget in self.pile_contents.winfo_children():
            widget.destroy()
        self.rows = {}
        for owner, count in enumerate(counts):
            for pile in range(count):
                default = (self.saved[owner][pile] if owner < len(self.saved)
                           and pile < len(self.saved[owner]) else {})
                value = self.cache.get((owner, pile), default)
                frame = tk.LabelFrame(self.pile_contents, text=f"{self.player_name(owner)} — Pile {pile + 1}", padx=6, pady=4)
                frame.pack(fill="x", pady=3)
                row = {"access": tk.StringVar(value=value.get("access", "owner")),
                       "ordering": tk.StringVar(value=("Ordered by size" if value.get("order_by") == "size"
                                                       else "Ordered by time") if value.get("ordered", False) else "Not ordered"),
                       "size_order": tk.StringVar(value=value.get("size_order", "up")),
                       "new_card": tk.StringVar(value=value.get("new_card", "top")), "frame": frame}
                self.rows[owner, pile] = row
                access_group = tk.Frame(frame)
                access_group.grid(row=0, column=0, sticky="w")
                tk.Label(access_group, text="Access:").pack(side="left")
                access = tk.OptionMenu(access_group, row["access"], "everyone", "team", "owner")
                access.pack(side="left")
                ordering_group = tk.Frame(frame)
                ordering_group.grid(row=0, column=1, sticky="w", padx=(12, 0))
                tk.Label(ordering_group, text="Ordering:").pack(side="left")
                ordering = tk.OptionMenu(ordering_group, row["ordering"], "Not ordered", "Ordered by size",
                                         "Ordered by time", command=lambda _: self.update_states())
                ordering.pack(side="left")
                position = tk.Frame(frame)
                position.grid(row=2, column=0, sticky="w")
                tk.Label(position, text="New card:").pack(side="left")
                tk.OptionMenu(position, row["new_card"], "top", "bottom").pack(side="left")
                size_direction = tk.Frame(frame)
                tk.Label(size_direction, text="Size order:").pack(side="left")
                tk.OptionMenu(size_direction, row["size_order"], "up", "down").pack(side="left")
                row.update(position=position, size_direction=size_direction,
                           access_group=access_group, ordering_group=ordering_group)
                frame.bind("<Configure>", lambda event, r=row: self.arrange_controls(r))
        self.update_states()
        self.parent.after_idle(self.fit_window)

    def arrange_controls(self, row):
        frame = row["frame"]
        if not frame.winfo_exists():
            return
        available = max(1, frame.winfo_width() - 16)
        groups = [row["access_group"], row["ordering_group"]]
        if row["ordering"].get() == "Ordered by time":
            groups.append(row["position"])
        else:
            row["position"].grid_remove()
        if row["ordering"].get() == "Ordered by size":
            groups.append(row["size_direction"])
        else:
            row["size_direction"].grid_remove()
        line, offset = 0, 0
        for group in groups:
            width = group.winfo_reqwidth()
            if offset and offset + width > available:
                line += 1
                offset = 0
            # Keep each row independent of the widths used on other rows.
            group.grid_configure(row=line, column=0, sticky="w", padx=(offset, 0))
            offset += width + 12

    def update_states(self):
        def enable(frame):
            for widget in frame.winfo_children():
                if "state" in widget.keys():
                    widget.configure(state="normal" if self.enabled_var.get() else "disabled")
                enable(widget)
        enable(self.options)
        self.shared_count.configure(state="normal" if self.enabled_var.get() and not self.unequal_var.get() else "disabled")
        if self.unequal_var.get():
            self.owner_counts_frame.pack(fill="x", before=self.pile_contents)
        else:
            self.owner_counts_frame.pack_forget()
        for row in self.rows.values():
            self.arrange_controls(row)
        self.parent.after_idle(self.arrange_all_controls)
        self.scroll_area.schedule_resize()

    def arrange_all_controls(self):
        for row in self.rows.values():
            self.arrange_controls(row)

    def values(self):
        counts = self.counts()
        return {"enable_personal_piles": self.enabled_var.get(), "personal_pile_count": int(self.count_var.get()),
                "unequal_personal_piles": self.unequal_var.get(),
                "personal_pile_counts": [int(var.get()) for var in self.owner_count_vars[:len(counts)]],
                "personal_pile_settings": [[self.row_value(self.rows[owner, pile])
                                            for pile in range(count)] for owner, count in enumerate(counts)]}
