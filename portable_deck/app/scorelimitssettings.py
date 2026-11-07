import tkinter as tk

class ScoreLimitsSettings:
    def __init__(self, parent, settings, scoring):
        self.scoring = scoring
        self.target = tk.BooleanVar(value=settings.get("enable_target_score", False))
        self.limit = tk.StringVar(value=str(settings.get("target_score", 100)))
        self.warning = tk.BooleanVar(value=settings.get("enable_score_warning", False))
        self.threshold = tk.StringVar(value=str(settings.get("score_warning", 80)))
        self.target_check = tk.Checkbutton(parent, text="Enable target score", variable=self.target, command=self.update)
        self.target_check.pack(anchor="w")
        row = tk.Frame(parent); row.pack(anchor="w", padx=18)
        tk.Label(row, text="Target score:").pack(side="left")
        self.target_input = tk.Spinbox(row, from_=1, to=1000000, width=8, textvariable=self.limit); self.target_input.pack(side="left")
        self.warning_check = tk.Checkbutton(parent, text="Enable score warning", variable=self.warning, command=self.update)
        self.warning_check.pack(anchor="w", padx=18)
        row = tk.Frame(parent); row.pack(anchor="w", padx=36)
        tk.Label(row, text="Warn when score reaches:").pack(side="left")
        self.warning_input = tk.Spinbox(row, from_=0, to=1000000, width=8, textvariable=self.threshold); self.warning_input.pack(side="left")
        scoring.trace_add("write", self.update)
        self.update()

    def update(self, *_):
        active = self.scoring.get()
        self.target_check.configure(state="normal" if active else "disabled")
        self.target_input.configure(state="normal" if active and self.target.get() else "disabled")
        self.warning_check.configure(state="normal" if active and self.target.get() else "disabled")
        self.warning_input.configure(state="normal" if active and self.target.get() and self.warning.get() else "disabled")

    def values(self):
        target, warning = int(self.limit.get()), int(self.threshold.get())
        if target < 1 or warning < 0 or (self.target.get() and self.warning.get() and warning >= target):
            raise ValueError("Target score must be positive; warning must be below the target and at least zero.")
        return {"enable_target_score": self.target.get(), "target_score": target,
                "enable_score_warning": self.warning.get(), "score_warning": warning}
