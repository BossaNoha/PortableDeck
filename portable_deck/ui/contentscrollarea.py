"""A scrollable area that requests only the height its contents need."""
import tkinter as tk


class ContentScrollArea(tk.Frame):
    def __init__(self, parent, width=394, fit_window=None):
        super().__init__(parent)
        self.fit_window = fit_window
        self.pending = False
        self.canvas = tk.Canvas(self, width=width, height=1, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.contents = tk.Frame(self.canvas)
        self.item = self.canvas.create_window((0, 0), window=self.contents, anchor="nw")
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        self.contents.bind("<Configure>", self.schedule_resize)
        self.root = self.winfo_toplevel()
        self.root_binding = self.root.bind("<Configure>", self.on_root_resize, add="+")
        self.bind("<Destroy>", self.on_destroy)
        # A local bind tag scrolls over labels and controls without a global binding.
        self.wheel_tag = f"ContentScrollArea_{id(self)}"
        self.bind_class(self.wheel_tag, "<MouseWheel>", self.on_mousewheel)

    def on_destroy(self, event):
        if event.widget == self:
            self.root.unbind("<Configure>", self.root_binding)
            self.unbind_class(self.wheel_tag, "<MouseWheel>")

    def on_root_resize(self, event):
        if event.widget == self.root:
            self.schedule_resize()

    def on_canvas_resize(self, event):
        self.canvas.itemconfigure(self.item, width=event.width)
        self.schedule_resize()

    def schedule_resize(self, _event=None):
        if not self.pending:
            self.pending = True
            self.after(20, self.resize_to_contents)

    def resize_to_contents(self):
        self.pending = False
        if not self.winfo_exists():
            return
        content_height = self.contents.winfo_reqheight()
        chrome = max(0, self.root.winfo_reqheight() - self.canvas.winfo_reqheight())
        budget = self.root.winfo_screenheight() - 100 - chrome
        if self.fit_window is None and self.root.winfo_height() > 1:
            budget = min(budget, self.root.winfo_height() - chrome)
        height = min(content_height, max(40, budget))
        if self.canvas.winfo_reqheight() != height:
            self.canvas.configure(height=height)
            if self.fit_window:
                self.after_idle(self.fit_window)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        overflowing = content_height > min(height, max(1, self.canvas.winfo_height()))
        if overflowing and not self.scrollbar.winfo_manager():
            self.scrollbar.pack(side="right", fill="y", before=self.canvas)
        elif not overflowing and self.scrollbar.winfo_manager():
            self.scrollbar.pack_forget()
            self.canvas.yview_moveto(0)
        self.add_wheel_tags(self)

    def add_wheel_tags(self, widget):
        tags = widget.bindtags()
        if self.wheel_tag not in tags:
            widget.bindtags((self.wheel_tag,) + tags)
        for child in widget.winfo_children():
            self.add_wheel_tags(child)

    def on_mousewheel(self, event):
        # Keep the native scroll behaviour of a card list within the area.
        if isinstance(event.widget, (tk.Listbox, tk.Scrollbar)):
            return
        if self.scrollbar.winfo_manager() and event.delta:
            steps = -int(event.delta / 120) or (-1 if event.delta > 0 else 1)
            self.canvas.yview_scroll(steps, "units")
            return "break"
