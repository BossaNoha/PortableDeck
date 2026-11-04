"""A settings section with a persistent heading and collapsible contents."""
import tkinter as tk


class CollapsibleSection(tk.Frame):
    def __init__(self, parent, title, on_toggle):
        super().__init__(parent)
        self.title = title
        self.on_toggle = on_toggle
        self.expanded = False
        self.button = tk.Button(self, text=f"{title} ▸", command=self.toggle)
        self.button.pack(anchor="w", pady=(0, 2))
        self.content = tk.LabelFrame(self, text=title, padx=8, pady=5)

    def toggle(self):
        self.expanded = not self.expanded
        if self.expanded:
            self.content.pack(fill="x", pady=(0, 4))
        else:
            self.content.pack_forget()
        self.button.configure(text=f"{self.title} {'▾' if self.expanded else '▸'}")
        self.after_idle(self.on_toggle)
