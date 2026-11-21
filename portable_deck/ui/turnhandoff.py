"""Client-only privacy curtain while a hotseat device changes hands."""
import tkinter as tk


class TurnHandoff:
    def __init__(self, gui):
        self.gui = gui
        self.visible = False

    def show(self):
        if self.visible:
            return
        self.visible = True
        self.widgets = [(widget, widget.pack_info())
                        for widget in (self.gui.options_bar, self.gui.layout_frame)]
        for widget, _ in self.widgets:
            widget.pack_forget()
        self.frame = tk.Frame(self.gui.root, padx=24, pady=24)
        self.frame.pack(fill="both", expand=True)
        panel = tk.Frame(self.frame)
        panel.place(relx=.5, rely=.5, anchor="center")
        tk.Label(panel, text="Pass the device to the next player", font=("TkDefaultFont", 18, "bold"),
                 wraplength=500, justify="center").pack(pady=(0, 12))
        tk.Label(panel, text="Cards stay hidden until the next player is ready.",
                 wraplength=500, justify="center").pack(pady=(0, 20))
        self.ready = tk.Button(panel, text="Start next turn — show cards", command=self.confirm)
        self.ready.pack(pady=5)
        self.back = tk.Button(panel, text="Cancel handoff", command=self.cancel)
        self.back.pack(pady=5)
        self.ready.focus_set()
        self.gui.root.update_idletasks()

    def confirm(self):
        if not self.visible or self.gui.turn_flow.completing:
            return None
        self.ready.configure(state="disabled")
        self.back.configure(state="disabled")
        try:
            result = self.gui.turn_flow.confirm()
            if result.success:
                self._reveal()
            return result
        finally:
            if self.visible:
                self.ready.configure(state="normal")
                self.back.configure(state="normal")

    def cancel(self):
        if self.visible and not self.gui.turn_flow.completing:
            result = self.gui.turn_flow.cancel()
            if result.success:
                self._reveal()
            return result

    def _reveal(self):
        self.frame.destroy()
        for widget, packing in self.widgets:
            widget.pack(**packing)
        self.visible = False
        self.gui.next_button.focus_set()
