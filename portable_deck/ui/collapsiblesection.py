"""A settings section with a persistent heading and collapsible contents."""
import tkinter as tk


class CollapsibleSection(tk.Frame):
    def __init__(self, parent, title, on_toggle):
        super().__init__(parent)
        self.title = title
        self.on_toggle = on_toggle
        self.expanded = False
        self.button = tk.Button(self, text=f"{title} ▸", command=self.toggle)
        self.default_button_colors = {key: self.button.cget(key) for key in ("background", "activebackground", "foreground", "activeforeground")}
        self.button.pack(anchor="w", pady=(0, 2))
        self.content = tk.LabelFrame(self, text=title, padx=8, pady=5)

    def set_enabled_indicator(self, enabled, show_colors=True):
        if not show_colors:
            self.button.configure(**self.default_button_colors)
            return
        color = "#c7e9c0" if enabled else "#f4b8b8"
        self.button.configure(background=color, activebackground=color, foreground="#172117", activeforeground="#172117")

    def toggle(self):
        self.expanded = not self.expanded
        if self.expanded:
            self.content.pack(fill="x", pady=(0, 4))
        else:
            self.content.pack_forget()
        self.button.configure(text=f"{self.title} {'▾' if self.expanded else '▸'}")
        self.after_idle(self.on_toggle)
