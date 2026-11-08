import tkinter as tk

class SpecialActionsSettings:
    def __init__(self, parent, settings, discard_var):
        self.enabled = tk.BooleanVar(value=settings.get("enable_special_actions", False))
        self.draw = tk.BooleanVar(value=settings.get("allow_insert_draw_deck", False))
        self.discard = tk.BooleanVar(value=settings.get("allow_insert_discard_pile", False))
        self.discard_var = discard_var
        tk.Checkbutton(parent, text="Enable special actions", variable=self.enabled, command=self.update).pack(anchor="w")
        self.draw_check = tk.Checkbutton(parent, text="Enable placing card at selected position in draw deck", variable=self.draw, wraplength=300, justify="left")
        self.draw_check.pack(anchor="w")
        self.discard_check = tk.Checkbutton(parent, text="Enable placing card at selected position in discard pile", variable=self.discard, wraplength=300, justify="left")
        self.discard_check.pack(anchor="w")
        discard_var.trace_add("write", self.update)
        self.update()
    def update(self, *_):
        self.draw_check.configure(state="normal" if self.enabled.get() else "disabled")
        self.discard_check.configure(state="normal" if self.enabled.get() and self.discard_var.get() else "disabled")
    def values(self):
        return {"enable_special_actions": self.enabled.get(), "allow_insert_draw_deck": self.draw.get(), "allow_insert_discard_pile": self.discard.get()}
