"""Opt-in controls for player interactions."""
import tkinter as tk
from ..core.interactions import INTERACTIONS

class InteractionSettings:
    def __init__(self, parent, settings, chips_var, discard_var):
        self.enabled = tk.BooleanVar(value=settings.get("enable_interactions", False))
        self.chips_var, self.discard_var = chips_var, discard_var
        self.variables = {key: tk.BooleanVar(value=settings.get("interaction_options", {}).get(key, False)) for key in INTERACTIONS}
        tk.Checkbutton(parent, text="Enable interactions", variable=self.enabled, command=self.update).pack(anchor="w")
        self.checks = {}
        for key, label in INTERACTIONS.items():
            check = tk.Checkbutton(parent, text=label, variable=self.variables[key], wraplength=300, justify="left")
            check.pack(anchor="w")
            self.checks[key] = check
        chips_var.trace_add("write", self.update)
        discard_var.trace_add("write", self.update)
        self.update()

    def update(self, *_):
        for key, check in self.checks.items():
            enabled = self.enabled.get() and (key != "steal_chips" or self.chips_var.get()) and (key != "discard_random_card" or self.discard_var.get())
            check.configure(state="normal" if enabled else "disabled")

    def values(self):
        return {"enable_interactions": self.enabled.get(), "interaction_options": {key: var.get() for key, var in self.variables.items()}}
