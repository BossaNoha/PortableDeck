"""Wrap settings sections at their natural widths without fixed columns."""
import tkinter as tk


class ResponsiveSections(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, width=1, height=1)
        self.sections = []
        self.pending = False
        self.bind("<Configure>", self.schedule_layout)

    def add(self, section):
        self.sections.append(section)
        section.bind("<Configure>", self.schedule_layout, add="+")
        self.schedule_layout()

    def preferred_width(self):
        return sum(section.winfo_reqwidth() + 8 for section in self.sections)

    def schedule_layout(self, _event=None):
        if not self.pending:
            self.pending = True
            self.after_idle(self.arrange)

    def arrange(self):
        self.pending = False
        if not self.winfo_exists():
            return
        available = max(1, self.winfo_width())
        x, y, row_height = 0, 0, 0
        for section in self.sections:
            width = min(section.winfo_reqwidth(), available)
            height = section.winfo_reqheight()
            if x and x + width > available:
                x = 0
                y += row_height + 6
                row_height = 0
            section.place(x=x, y=y, width=width, height=height)
            x += width + 8
            row_height = max(row_height, height)
        height = max(1, y + row_height)
        if self.winfo_reqheight() != height:
            self.configure(height=height)
