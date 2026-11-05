"""Roles, named teams and exclusive player assignments."""
import tkinter as tk
from ..ui.contentscrollarea import ContentScrollArea


class RolesTeamsSettings:
    def __init__(self, parent, settings, players_var, custom_names_var, player_name, fit_window):
        self.parent = parent
        self.players_var = players_var
        self.custom_names_var = custom_names_var
        self.player_name = player_name or (lambda index: f"Player {index + 1}")
        self.fit_window = fit_window
        self.enabled_var = tk.BooleanVar(value=settings.get("enable_roles_teams", False))
        self.dealer_var = tk.BooleanVar(value=settings.get("enable_dealer", False))
        self.teams_var = tk.BooleanVar(value=settings.get("enable_teams", False))
        self.count_var = tk.StringVar(value=str(settings.get("team_count", 1)))
        self.name_vars = [tk.StringVar(value=name) for name in settings.get("team_names", [])]
        self.assignments = [tk.StringVar(value=value or "") for value in settings.get("player_teams", [])]
        saved_dealers = settings.get("dealer_players")
        self.dealer_assignments = [tk.BooleanVar(value=value) for value in saved_dealers] if saved_dealers else [
            tk.BooleanVar(value=value == "dealer") for value in settings.get("player_teams", [])]
        for var in self.assignments:
            if var.get() == "dealer":
                var.set("")
        self.checks = []
        self.name_entries = []
        self.player_checks = []
        self.building = False
        tk.Checkbutton(parent, text="Enable roles/teams", variable=self.enabled_var,
                       command=self.update_states).pack(anchor="w")
        self.options = tk.Frame(parent)
        self.options.pack(fill="x")
        tk.Checkbutton(self.options, text="Enable dealer", variable=self.dealer_var,
                       command=self.rebuild).pack(anchor="w")
        tk.Checkbutton(self.options, text="Enable teams", variable=self.teams_var,
                       command=self.rebuild).pack(anchor="w")
        count_row = tk.Frame(self.options)
        count_row.pack(anchor="w")
        tk.Label(count_row, text="Teams (including Dealer):").pack(side="left")
        self.count_input = tk.Spinbox(count_row, from_=1, to=20, width=5, textvariable=self.count_var)
        self.count_input.pack(side="left", padx=6)
        tk.Label(self.options, text="One regular team per player; Dealer is independent.\nDealer has no special privileges.",
                 justify="left").pack(anchor="w", pady=4)
        self.scroll_area = ContentScrollArea(self.options, width=350, fit_window=fit_window)
        self.scroll_area.pack(fill="x")
        self.contents = self.scroll_area.contents
        self.count_var.trace_add("write", self.rebuild)
        self.players_var.trace_add("write", self.rebuild)
        self.custom_names_var.trace_add("write", self.rebuild)
        self.rebuild()

    def team_ids(self, count):
        regular = count - int(self.dealer_var.get()) if self.teams_var.get() else 0
        return (["dealer"] if self.dealer_var.get() else []) + [f"team_{i + 1}" for i in range(regular)]

    def rebuild(self, *_):
        if self.building:
            return
        try:
            players, count = int(self.players_var.get()), int(self.count_var.get())
            if not 1 <= players <= 20 or count < 1:
                return
        except ValueError:
            return
        self.building = True
        try:
            count = min(count, players)
            if self.count_var.get() != str(count):
                self.count_var.set(str(count))
            self.count_input.configure(to=players)
            while len(self.assignments) < players:
                self.assignments.append(tk.StringVar(value=""))
            while len(self.dealer_assignments) < players:
                self.dealer_assignments.append(tk.BooleanVar(value=False))
            while len(self.name_vars) < count:
                self.name_vars.append(tk.StringVar(value=f"Team {len(self.name_vars) + 1}"))
            for widget in self.contents.winfo_children():
                widget.destroy()
            self.checks, self.name_entries, self.player_checks = [], [], []
            for team_id in self.team_ids(count):
                title = "Dealer" if team_id == "dealer" else f"Team {int(team_id.split('_')[1])}"
                frame = tk.LabelFrame(self.contents, text=title, padx=6, pady=4)
                frame.pack(fill="x", pady=3)
                if team_id != "dealer" and self.custom_names_var.get():
                    index = int(team_id.split("_")[1]) - 1
                    entry = tk.Entry(frame, textvariable=self.name_vars[index], width=24)
                    entry.pack(anchor="w", fill="x", pady=(0, 4))
                    self.name_entries.append(entry)
                for player in range(players):
                    selected = tk.BooleanVar(value=self.dealer_assignments[player].get() if team_id == "dealer" else self.assignments[player].get() == team_id)
                    check = tk.Checkbutton(frame, text=self.player_name(player), variable=selected,
                                           command=lambda p=player, t=team_id, v=selected: self.assign(p, t, v))
                    check.pack(anchor="w")
                    self.checks.append((player, team_id, selected))
                    self.player_checks.append((player, check))
            self.update_states()
        finally:
            self.building = False
        self.parent.after_idle(self.fit_window)

    def assign(self, player, team_id, selected):
        if team_id == "dealer":
            self.dealer_assignments[player].set(selected.get())
        else:
            self.assignments[player].set(team_id if selected.get() else "")
        for owner, team, variable in self.checks:
            if owner == player:
                variable.set(self.dealer_assignments[player].get() if team == "dealer" else self.assignments[player].get() == team)

    def update_names(self):
        for player, check in self.player_checks:
            check.configure(text=self.player_name(player))

    def update_states(self):
        def enable(frame):
            for widget in frame.winfo_children():
                if "state" in widget.keys():
                    widget.configure(state="normal" if self.enabled_var.get() else "disabled")
                enable(widget)
        enable(self.options)
        self.count_input.configure(state="normal" if self.enabled_var.get() and self.teams_var.get() else "disabled")
        self.scroll_area.schedule_resize()

    def values(self):
        players, count = int(self.players_var.get()), int(self.count_var.get())
        if not 1 <= count <= players:
            raise ValueError("The total number of teams, including Dealer, must not exceed the player count.")
        ids = self.team_ids(count)
        regular = len(ids) - int(self.dealer_var.get())
        names = [var.get().strip() for var in self.name_vars[:regular]] if self.custom_names_var.get() else [f"Team {i + 1}" for i in range(regular)]
        if any(not name for name in names):
            if self.enabled_var.get() and self.teams_var.get():
                raise ValueError("Enter a name for each team.")
            names = [name or f"Team {i + 1}" for i, name in enumerate(names)]
        return {"enable_roles_teams": self.enabled_var.get(), "enable_dealer": self.dealer_var.get(),
                "enable_teams": self.teams_var.get(), "team_count": count, "team_names": names,
                "player_teams": [var.get() if var.get() in ids else None for var in self.assignments[:players]],
                "dealer_players": [var.get() for var in self.dealer_assignments[:players]]}
