import tkinter as tk

class PlayerLeavingSettings:
    def __init__(self, parent, settings, scoring, chips, limits):
        self.scoring, self.chips, self.limits = scoring, chips, limits
        saved = dict(settings.get("leave_conditions", {}))
        if saved.pop("any_time", False):
            saved.update(own_score=False, opponent_score=False, no_chips=False)
        self.match = tk.StringVar(value="At least one condition" if saved.get("match") == "any" else "All conditions")
        self.allow_return = tk.BooleanVar(value=settings.get("enable_player_return", False))
        self.enabled = tk.BooleanVar(value=settings.get("enable_player_leaving", False))
        self.variables = {key: tk.BooleanVar(value=saved.get(key, False)) for key in ("own_score", "opponent_score", "no_chips")}
        self.modes = {key: tk.StringVar(value=saved.get(key + "_at", "target")) for key in ("own_score", "opponent_score")}
        tk.Checkbutton(parent, text="Enable leaving session", variable=self.enabled, command=self.update).pack(anchor="w")
        tk.Checkbutton(parent, text="Enable player return to session", variable=self.allow_return).pack(anchor="w")
        self.checks, self.menus = {}, {}
        labels = {"own_score": "Restrict leaving before player reaches score",
                  "opponent_score": "Restrict leaving before opponent reaches score",
                  "no_chips": "Restrict leaving before running out of chips"}
        for key, label in labels.items():
            check = tk.Checkbutton(parent, text=label, variable=self.variables[key], command=self.update, wraplength=300, justify="left")
            check.pack(anchor="w"); self.checks[key] = check
            if key in self.modes:
                menu = tk.OptionMenu(parent, self.modes[key], "target", "warning")
                menu.pack(anchor="w", padx=20); self.menus[key] = menu
        self.match_frame = tk.Frame(parent)
        tk.Label(self.match_frame, text="Required:").pack(side="left")
        self.match_menu = tk.OptionMenu(self.match_frame, self.match, "All conditions", "At least one condition")
        self.match_menu.pack(side="left")
        for variable in (scoring, chips, limits.target, limits.warning):
            variable.trace_add("write", self.update)
        self.update()

    def update(self, *_):
        enabled = self.enabled.get()
        score = self.scoring.get() and self.limits.target.get()
        for key, check in self.checks.items():
            available = self.chips.get() if key == "no_chips" else score
            check.configure(state="normal" if enabled and available else "disabled")
        selected = sum(var.get() and (self.chips.get() if key == "no_chips" else score) for key, var in self.variables.items())
        if selected > 1:
            self.match_frame.pack(anchor="w", pady=5)
        else:
            self.match_frame.pack_forget()
        self.match_menu.configure(state="normal" if enabled else "disabled")
        for key, menu in self.menus.items():
            if not self.limits.warning.get() and self.modes[key].get() == "warning":
                self.modes[key].set("target")
            options = menu["menu"]
            options.entryconfigure(1, state="normal" if self.limits.warning.get() else "disabled")
            menu.configure(state="normal" if enabled and score and self.variables[key].get() else "disabled")

    def values(self):
        rules = {key: var.get() for key, var in self.variables.items()}
        rules["match"] = "any" if self.match.get() == "At least one condition" else "all"
        rules.update({key + "_at": var.get() for key, var in self.modes.items()})
        return {"enable_player_return": self.allow_return.get(), "enable_player_leaving": self.enabled.get(), "leave_conditions": rules}
