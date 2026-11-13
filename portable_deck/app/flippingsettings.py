import tkinter as tk

class FlippingSettings:
    def __init__(self, parent, settings, table_var, player_rows_var):
        self.enabled = tk.BooleanVar(value=settings.get("enable_flipping", False))
        self.table_var, self.player_rows_var = table_var, player_rows_var
        self.variables = {key: tk.BooleanVar(value=settings.get(key, False)) for key in
                          ("allow_flip_hand", "allow_flip_table", "allow_flip_player_cards")}
        tk.Checkbutton(parent, text="Enable flipping cards", variable=self.enabled, command=self.update).pack(anchor="w")
        self.checks = {}
        for key, label in (("allow_flip_hand", "Enable flipping cards in hand"),
                           ("allow_flip_table", "Enable flipping cards on table"),
                           ("allow_flip_player_cards", "Enable flipping cards in front of players")):
            check = tk.Checkbutton(parent, text=label, variable=self.variables[key], wraplength=300, justify="left")
            check.pack(anchor="w"); self.checks[key] = check
        table_var.trace_add("write", self.update)
        player_rows_var.trace_add("write", self.update)
        self.update()
    def update(self, *_):
        for key, check in self.checks.items():
            available = self.enabled.get() and (key == "allow_flip_hand" or self.table_var.get())
            if key == "allow_flip_player_cards":
                available = available and self.player_rows_var.get()
            check.configure(state="normal" if available else "disabled")
    def values(self):
        return {"enable_flipping": self.enabled.get(), **{key: var.get() for key, var in self.variables.items()}}
