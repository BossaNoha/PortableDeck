"""Per-player, per-pile access and ordering preferences."""
import tkinter as tk
from ..ui.contentscrollarea import ContentScrollArea


class PersonalPileSettings:
    def __init__(self, parent, settings, players_var, fit_window):
        self.parent = parent
        self.players_var = players_var
        self.fit_window = fit_window
        legacy_count = settings.get("personal_discard_pile_count", 0)
        self.enabled_var = tk.BooleanVar(value=settings.get("enable_personal_piles", legacy_count > 0))
        self.count_var = tk.StringVar(value=str(settings.get("personal_pile_count", legacy_count or 1)))
        self.saved = settings.get("personal_pile_settings", [])
        self.rows = {}
        self.cache = {}
        tk.Checkbutton(parent, text="Enable personal piles", variable=self.enabled_var,
                       command=self.update_states).pack(anchor="w")
        self.options = tk.Frame(parent)
        self.options.pack(fill="x")
        count_row = tk.Frame(self.options)
        count_row.pack(anchor="w")
        tk.Label(count_row, text="Personal piles per player:").pack(side="left")
        tk.Spinbox(count_row, from_=1, to=20, width=5, textvariable=self.count_var).pack(side="left", padx=6)
        tk.Label(self.options, text="Team access currently allows only the owner.",
                 fg="#666666").pack(anchor="w", pady=4)
        self.scroll_area = ContentScrollArea(self.options, fit_window=fit_window)
        self.scroll_area.pack(fill="both", expand=True)
        self.canvas = self.scroll_area.canvas
        self.contents = self.scroll_area.contents
        self.count_var.trace_add("write", self.rebuild)
        players_var.trace_add("write", self.rebuild)
        self.rebuild()

    def row_value(self, row):
        ordering = row["ordering"].get()
        return {"access": row["access"].get(), "ordered": ordering != "Not ordered",
                "order_by": "size" if ordering == "Ordered by size" else "time",
                "new_card": row["new_card"].get(), "size_order": row["size_order"].get()}

    def rebuild(self, *_):
        try:
            count, players = int(self.count_var.get()), int(self.players_var.get())
            if not 1 <= count <= 20 or not 1 <= players <= 20:
                return
        except ValueError:
            return
        self.cache.update({key: self.row_value(row) for key, row in self.rows.items()})
        for widget in self.contents.winfo_children():
            widget.destroy()
        self.rows = {}
        for owner in range(players):
            for pile in range(count):
                default = (self.saved[owner][pile] if owner < len(self.saved)
                           and pile < len(self.saved[owner]) else {})
                value = self.cache.get((owner, pile), default)
                frame = tk.LabelFrame(self.contents, text=f"Player {owner + 1} — Pile {pile + 1}", padx=6, pady=4)
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
        for row in self.rows.values():
            self.arrange_controls(row)
        self.parent.after_idle(self.arrange_all_controls)
        self.scroll_area.schedule_resize()

    def arrange_all_controls(self):
        for row in self.rows.values():
            self.arrange_controls(row)

    def values(self):
        count, players = int(self.count_var.get()), int(self.players_var.get())
        if not 1 <= count <= 20 or not 1 <= players <= 20:
            raise ValueError("Personal pile count must be between 1 and 20.")
        return {"enable_personal_piles": self.enabled_var.get(), "personal_pile_count": count,
                "personal_pile_settings": [[self.row_value(self.rows[owner, pile])
                                            for pile in range(count)] for owner in range(players)]}
