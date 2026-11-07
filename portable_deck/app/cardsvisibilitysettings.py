"""Edit a matrix of hand owners and permitted viewers."""
import copy
import tkinter as tk

class CardsVisibilitySettings:
    def __init__(self, parent, settings, players_var, player_name, roles):
        self.parent, self.players_var, self.roles = parent, players_var, roles
        self.player_name = player_name or (lambda i: f"Player {i + 1}")
        self.enabled = tk.BooleanVar(value=settings.get("enable_cards_visibility", False))
        self.rules = copy.deepcopy(settings.get("cards_visibility", []))
        tk.Checkbutton(parent, text="Enable cards visibility", variable=self.enabled, command=self.update).pack(anchor="w")
        self.button = tk.Button(parent, text="Configure hand visibility…", command=self.show)
        self.button.pack(anchor="w")
        self.update()

    def update(self):
        self.button.configure(state="normal" if self.enabled.get() else "disabled")

    def values(self):
        count = int(self.players_var.get())
        rules = []
        for owner in range(count):
            rule = self.rules[owner] if owner < len(self.rules) else {"players": [owner], "teams": []}
            rules.append({"players": [i for i in rule["players"] if i < count], "teams": list(rule["teams"])})
        return {"enable_cards_visibility": self.enabled.get(), "cards_visibility": rules}

    def show(self):
        count = int(self.players_var.get())
        data = self.values()["cards_visibility"]
        dialog = tk.Toplevel(self.parent)
        dialog.title("Cards visibility — hand permissions")
        dialog.transient(self.parent.winfo_toplevel())
        dialog.grab_set()
        tk.Label(dialog, text="Rows: whose hand. Columns: who may see it. Permissions are directional.").pack(padx=12, pady=10)
        area = tk.Frame(dialog)
        area.pack(fill="both", expand=True)
        canvas = tk.Canvas(area, highlightthickness=0)
        vertical = tk.Scrollbar(area, command=canvas.yview)
        vertical.pack(side="right", fill="y")
        horizontal = tk.Scrollbar(dialog, orient="horizontal", command=canvas.xview)
        horizontal.pack(fill="x")
        canvas.pack(fill="both", expand=True)
        canvas.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        grid = tk.Frame(canvas)
        canvas.create_window((0, 0), window=grid, anchor="nw")
        grid.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        columns = [("players", i, self.player_name(i)) for i in range(count)]
        if self.roles.enabled_var.get():
            for team in self.roles.team_ids(int(self.roles.count_var.get())):
                label = "Dealer" if team == "dealer" else f"Team {team.split('_')[1]}"
                if team != "dealer" and self.roles.custom_names_var.get():
                    label = self.roles.name_vars[int(team.split('_')[1]) - 1].get() or label
                columns.append(("teams", team, label))
        tk.Label(grid, text="Hand owner ↓ / Viewer →").grid(row=0, column=0, padx=8, pady=6)
        for column, (_, _, label) in enumerate(columns, 1):
            tk.Label(grid, text=label, wraplength=110).grid(row=0, column=column, padx=8, pady=6)
        variables = []
        for owner in range(count):
            tk.Label(grid, text=self.player_name(owner)).grid(row=owner + 1, column=0, sticky="w", padx=8)
            row = []
            for column, (kind, key, _) in enumerate(columns, 1):
                variable = tk.BooleanVar(value=key in data[owner][kind])
                tk.Checkbutton(grid, variable=variable).grid(row=owner + 1, column=column)
                row.append(variable)
            variables.append(row)
        def apply():
            visible_teams = {key for kind, key, _ in columns if kind == "teams"}
            self.rules = [{"players": [], "teams": [team for team in rule["teams"] if team not in visible_teams]}
                          for rule in data]
            for owner, row in enumerate(variables):
                for variable, (kind, key, _) in zip(row, columns):
                    if variable.get():
                        self.rules[owner][kind].append(key)
            dialog.destroy()
        dialog.protocol("WM_DELETE_WINDOW", apply)
        buttons = tk.Frame(dialog)
        buttons.pack(fill="x", padx=10, pady=10)
        tk.Label(buttons, text="Changes go into the settings form.\nUse current settings applies and saves them.", justify="left").pack(side="left", padx=(0, 12))
        tk.Button(buttons, text="Apply", command=apply).pack(side="right")
        tk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right", padx=6)
        dialog.update_idletasks()
        dialog.geometry(f"{min(grid.winfo_reqwidth() + 40, dialog.winfo_screenwidth() - 80)}x{min(grid.winfo_reqheight() + 130, dialog.winfo_screenheight() - 100)}")
