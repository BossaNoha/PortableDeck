"""Tkinter rendering of the shared session rules overview."""
import tkinter as tk
from ..core.rulesoverview import (
    build_rules_overview, configuration_summary, format_rule_entry,
    session_rule_sections,  # Backward-compatible import for existing clients.
)


def show_rules_overview(gui):
    overview = build_rules_overview(gui.game)
    window = tk.Toplevel(gui.root)
    window.title("Overview rules")
    window.transient(gui.root)
    window.geometry(f"{min(700, window.winfo_screenwidth()-80)}x{min(620, window.winfo_screenheight()-100)}")
    tk.Label(window, text=configuration_summary(overview),
             wraplength=620, justify="left", padx=12, pady=10).pack(anchor="w")
    frame = tk.Frame(window)
    frame.pack(fill="both", expand=True, padx=12)
    text = tk.Text(frame, wrap="word", padx=10, pady=8, width=60)
    bar = tk.Scrollbar(frame, command=text.yview)
    bar.pack(side="right", fill="y")
    text.pack(fill="both", expand=True)
    text.configure(yscrollcommand=bar.set)
    text.tag_configure("heading", font=("TkDefaultFont", 11, "bold"), spacing1=8, spacing3=4)
    for section in overview.sections:
        text.insert("end", section.title + "\n", "heading")
        for entry in section.entries:
            text.insert("end", "• " + format_rule_entry(entry) + "\n")
        text.insert("end", "\n")
    text.configure(state="disabled")
    tk.Button(window, text="Close", command=window.destroy).pack(anchor="e", padx=12, pady=10)
    return window
