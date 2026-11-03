"""Minimal local Tkinter front end for the Form 22 generator."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from form22_bridge import run


def main() -> None:
    root = tk.Tk()
    root.title("NC Form 22 Generator")
    vars_ = {k: tk.StringVar() for k in ("payroll", "doi", "template", "output")}
    default_template = Path(__file__).resolve().parents[1] / "templates" / "form22.pdf"
    if default_template.is_file():
        vars_["template"].set(str(default_template))

    def row(i: int, label: str, key: str, browse: bool = False, save: bool = False) -> None:
        tk.Label(root, text=label).grid(row=i, column=0, sticky="e")
        tk.Entry(root, textvariable=vars_[key], width=60).grid(row=i, column=1)
        if browse:
            def pick() -> None:
                chosen = (filedialog.asksaveasfilename(defaultextension=".pdf") if save
                          else filedialog.askopenfilename())
                if chosen:
                    vars_[key].set(chosen)
            tk.Button(root, text="Browse", command=pick).grid(row=i, column=2)

    row(0, "Payroll (CSV/JSON)", "payroll", True)
    row(1, "Date of injury (YYYY-MM-DD)", "doi")
    row(2, "Form 22 template", "template", True)
    row(3, "Output PDF", "output", True, True)

    def go() -> None:
        result = run(*(vars_[k].get() for k in ("payroll", "doi", "template", "output")))
        (messagebox.showinfo if result["ok"] else messagebox.showerror)("Form 22", result["message"])

    tk.Button(root, text="Generate", command=go).grid(row=4, column=1)
    root.mainloop()


if __name__ == "__main__":
    main()
