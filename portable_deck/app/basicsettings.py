"""Application-wide saving and exit preferences."""
import tkinter as tk
from ..ui.collapsiblesection import CollapsibleSection


class BasicSettingsPanel:
    def __init__(self, parent, settings, fit_window=lambda: None):
        self.fit_window = fit_window
        self.undo_var = tk.BooleanVar(value=bool(settings.get("enable_undo", False)))
        self.autosave_var = tk.BooleanVar(value=settings.get("autosave_enabled", True))
        self.count_var = tk.StringVar(value=str(settings.get("autosave_count", 5)))
        self.confirm_exit_var = tk.BooleanVar(value=settings.get("require_exit_confirmation", True))
        self.section = CollapsibleSection(parent, "Basic Settings", fit_window)
        self.section.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        self.frame = self.section.content
        self.button = self.section.button
        tk.Checkbutton(self.frame, text="Autosave", variable=self.autosave_var,
                       command=self.update_controls).grid(row=0, column=0, sticky="w")
        self.count_frame = tk.Frame(self.frame)
        self.count_frame.grid(row=1, column=0, sticky="w", padx=(22, 0))
        tk.Label(self.count_frame, text="Autosaves to keep:").pack(side="left")
        tk.Spinbox(self.count_frame, from_=1, to=1000, width=6,
                   textvariable=self.count_var).pack(side="left", padx=6)
        tk.Checkbutton(self.frame, text="Require exit confirmation",
                       variable=self.confirm_exit_var).grid(row=2, column=0, sticky="w")
        tk.Checkbutton(self.frame, text="Enable Undo", variable=self.undo_var).grid(
            row=3, column=0, sticky="w"
        )
        self.update_controls()

    def update_controls(self):
        if self.autosave_var.get():
            self.count_frame.grid()
        else:
            self.count_frame.grid_remove()

        self.frame.after_idle(self.fit_window)

    def toggle(self):
        self.section.toggle()

    def values(self):
        count = int(self.count_var.get()) if self.autosave_var.get() else 5
        if not 1 <= count <= 1000:
            raise ValueError("Autosaves to keep must be between 1 and 1000.")
        return {"enable_undo": self.undo_var.get(), "autosave_enabled": self.autosave_var.get(), "autosave_count": count,
                "require_exit_confirmation": self.confirm_exit_var.get()}
