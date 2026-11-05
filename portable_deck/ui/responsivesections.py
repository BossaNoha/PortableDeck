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
        if not self.sections:
            return
        gap = 10
        # Independent columns prevent a tall category leaving empty space
        # beneath all the shorter categories alongside it.
        natural_width = max(section.winfo_reqwidth() for section in self.sections)
        columns = max(1, min(len(self.sections), (available + gap) // (natural_width + gap)))
        column_width = max(1, (available - gap * (columns - 1)) // columns)
        bottoms = [0] * columns
        for section in self.sections:
            column = min(range(columns), key=lambda index: (bottoms[index], index))
            height = section.winfo_reqheight()
            section.place(x=column * (column_width + gap), y=bottoms[column],
                          width=column_width, height=height)
            bottoms[column] += height + gap
        height = max(1, max(bottoms) - gap)
        if self.winfo_reqheight() != height:
            self.configure(height=height)
