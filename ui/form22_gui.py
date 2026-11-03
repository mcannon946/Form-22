"""Tkinter window for the NC Form 22 Generator (offline)."""
from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app_paths import default_output_dir  # noqa: E402
from form22_bridge import preview, run  # noqa: E402
from form22_version import APP_NAME, APP_VERSION, FORM_REVISION  # noqa: E402


def open_path(path: Path, select: bool = False) -> None:
    if sys.platform == "win32":
        if select:
            subprocess.Popen(["explorer", "/select,", str(path)])  # noqa: S603,S607
        else:
            os.startfile(str(path))  # type: ignore[attr-defined]  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path.parent if select else path)])
    else:
        subprocess.Popen(["xdg-open", str(path.parent if select else path)])


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.minsize(640, 480)
        self.payroll = tk.StringVar()
        self.doi = tk.StringVar()
        self.alt_template = tk.StringVar()
        self.last_output: Path | None = None
        self._build()

    def _build(self) -> None:
        frm = ttk.Frame(self, padding=16)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)
        ttk.Label(frm, text=APP_NAME, font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(frm, text=f"Fills the official NC Industrial Commission Form 22 (rev. {FORM_REVISION}). "
                  "Works offline; nothing leaves this computer.", wraplength=580).grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Label(frm, text="1. Payroll file (CSV or JSON)").grid(row=2, column=0, columnspan=3, sticky="w")
        ttk.Entry(frm, textvariable=self.payroll).grid(row=3, column=0, columnspan=2, sticky="ew", padx=(0, 6))
        ttk.Button(frm, text="Browse...", command=self.pick_payroll).grid(row=3, column=2)

        ttk.Label(frm, text="2. Date of injury (YYYY-MM-DD)").grid(row=4, column=0, columnspan=3, sticky="w", pady=(10, 0))
        ttk.Entry(frm, textvariable=self.doi, width=16).grid(row=5, column=0, sticky="w")

        ttk.Button(frm, text="Check payroll", command=self.check).grid(row=6, column=0, sticky="w", pady=10)
        self.summary = tk.Text(frm, height=8, wrap="word", state="disabled", relief="flat", background="#f3f3f3")
        self.summary.grid(row=7, column=0, columnspan=3, sticky="nsew")
        frm.rowconfigure(7, weight=1)

        self.generate_btn = ttk.Button(frm, text="Generate Form 22", command=self.generate)
        self.generate_btn.grid(row=8, column=0, columnspan=3, pady=12, sticky="ew")

        self.open_row = ttk.Frame(frm)
        self.open_row.grid(row=9, column=0, columnspan=3, sticky="w")
        ttk.Button(self.open_row, text="Open PDF", command=lambda: self.last_output and open_path(self.last_output)
                   ).pack(side="left")
        ttk.Button(self.open_row, text="Show in folder",
                   command=lambda: self.last_output and open_path(self.last_output, True)).pack(side="left", padx=6)
        self.open_row.grid_remove()

        adv = ttk.LabelFrame(frm, text="Advanced", padding=8)
        adv.grid(row=10, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        adv.columnconfigure(0, weight=1)
        ttk.Label(adv, text=f"The bundled August 2026 Form 22 is the verified default. "
                  "Only choose another template if you know it is compatible.", wraplength=560).grid(
            row=0, column=0, columnspan=3, sticky="w")
        ttk.Entry(adv, textvariable=self.alt_template).grid(row=1, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(adv, text="Browse...", command=self.pick_template).grid(row=1, column=1)
        ttk.Button(adv, text="Use default", command=lambda: self.alt_template.set("")).grid(row=1, column=2, padx=6)

    def _set_summary(self, text: str) -> None:
        self.summary.configure(state="normal")
        self.summary.delete("1.0", "end")
        self.summary.insert("1.0", text)
        self.summary.configure(state="disabled")

    def pick_payroll(self) -> None:
        chosen = filedialog.askopenfilename(
            title="Select payroll file", filetypes=[("Payroll files", "*.csv *.json"), ("All files", "*.*")])
        if chosen:
            self.payroll.set(chosen)

    def pick_template(self) -> None:
        chosen = filedialog.askopenfilename(title="Select alternate Form 22 template",
                                            filetypes=[("PDF files", "*.pdf")])
        if chosen:
            self.alt_template.set(chosen)

    def check(self) -> bool:
        result = preview(self.payroll.get(), self.doi.get())
        self._set_summary(("Ready to generate.\n\n" if result["ok"] else "Please fix this first:\n\n")
                          + result["message"])
        return result["ok"]

    def generate(self) -> None:
        self.open_row.grid_remove()
        if not self.check():
            return
        default_name = f"Form22_{self.doi.get().strip()}.pdf"
        out = filedialog.asksaveasfilename(
            title="Save completed Form 22", defaultextension=".pdf", initialfile=default_name,
            initialdir=str(default_output_dir()), filetypes=[("PDF files", "*.pdf")])
        if not out:
            return
        result = run(self.payroll.get(), self.doi.get(), out, self.alt_template.get() or None)
        if result["ok"]:
            self.last_output = Path(result["output"])
            self.open_row.grid()
            messagebox.showinfo(APP_NAME, "Your completed Form 22 was created.\n\n" + result["message"])
        else:
            messagebox.showerror(APP_NAME, result["message"])
