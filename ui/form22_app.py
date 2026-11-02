"""Offline desktop UI for the NC Form 22 generator."""

from __future__ import annotations

import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from generate_form22 import generate_form22
from payroll_importer import load_payroll


class Form22App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("NC Form 22 Generator")
        self.geometry("760x470")
        self.minsize(680, 430)

        self.template_var = tk.StringVar()
        self.payroll_var = tk.StringVar()
        self.doi_var = tk.StringVar()
        self.output_var = tk.StringVar()

        self.status_var = tk.StringVar(
            value="Select the blank Form 22 PDF and payroll file."
        )

        self._build()

    def _build(self):
        pad = {"padx": 12, "pady": 7}

        frame = ttk.Frame(self, padding=18)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="NC Form 22 Generator",
            font=("Segoe UI", 20, "bold"),
        ).grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="w",
            **pad,
        )

        ttk.Label(
            frame,
            text=(
                "Offline form-filling utility. "
                "This tool does not calculate average weekly wage "
                "or compensation rate."
            ),
        ).grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="w",
            **pad,
        )

        self._file_row(
            frame,
            2,
            "Blank Form 22 PDF",
            self.template_var,
            [("PDF files", "*.pdf")],
        )

        self._file_row(
            frame,
            3,
            "Payroll CSV or JSON",
            self.payroll_var,
            [
                ("Payroll files", "*.csv *.json"),
                ("All files", "*.*"),
            ],
        )

        ttk.Label(
            frame,
            text="Date of injury (YYYY-MM-DD)",
        ).grid(
            row=4,
            column=0,
            sticky="w",
            **pad,
        )

        ttk.Entry(
            frame,
            textvariable=self.doi_var,
            width=28,
        ).grid(
            row=4,
            column=1,
            sticky="ew",
            **pad,
        )

        ttk.Label(
            frame,
            text="Output PDF",
        ).grid(
            row=5,
            column=0,
            sticky="w",
            **pad,
        )

        ttk.Entry(
            frame,
            textvariable=self.output_var,
        ).grid(
            row=5,
            column=1,
            sticky="ew",
            **pad,
        )

        ttk.Button(
            frame,
            text="Choose output",
            command=self._choose_output,
        ).grid(
            row=5,
            column=2,
            sticky="ew",
            **pad,
        )

        ttk.Separator(frame).grid(
            row=6,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=12,
            pady=14,
        )

        ttk.Button(
            frame,
            text="Generate Form 22",
            command=self._generate,
        ).grid(
            row=7,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=12,
            pady=10,
            ipady=8,
        )

        ttk.Label(
            frame,
            textvariable=self.status_var,
            wraplength=690,
        ).grid(
            row=8,
            column=0,
            columnspan=3,
            sticky="w",
            **pad,
        )

        frame.columnconfigure(1, weight=1)

    def _file_row(self, frame, row, label, variable, filetypes):
        ttk.Label(
            frame,
            text=label,
        ).grid(
            row=row,
            column=0,
            sticky="w",
            padx=12,
            pady=7,
        )

        ttk.Entry(
            frame,
            textvariable=variable,
        ).grid(
            row=row,
            column=1,
            sticky="ew",
            padx=12,
            pady=7,
        )

        ttk.Button(
            frame,
            text="Browse",
            command=lambda: self._choose_file(variable, filetypes),
        ).grid(
            row=row,
            column=2,
            sticky="ew",
            padx=12,
            pady=7,
        )

    def _choose_file(self, variable, filetypes):
        chosen = filedialog.askopenfilename(filetypes=filetypes)

        if chosen:
            variable.set(chosen)

            if variable is self.payroll_var and not self.output_var.get():
                self.output_var.set(
                    str(Path(chosen).with_name("completed_form22.pdf"))
                )

    def _choose_output(self):
        chosen = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
        )

        if chosen:
            self.output_var.set(chosen)

    def _validate(self):
        values = [
            self.template_var.get(),
            self.payroll_var.get(),
            self.doi_var.get(),
            self.output_var.get(),
        ]

        if not all(value.strip() for value in values):
            raise ValueError(
                "Choose the template, payroll file, "
                "date of injury, and output PDF."
            )

        if Path(self.template_var.get()).suffix.lower() != ".pdf":
            raise ValueError(
                "The Form 22 template must be a PDF."
            )

        if Path(self.payroll_var.get()).suffix.lower() not in {
            ".csv",
            ".json",
        }:
            raise ValueError(
                "The payroll file must be CSV or JSON."
            )

    def _generate(self):
        try:
            self._validate()

            rows = load_payroll(
                self.payroll_var.get()
            )

            generate_form22(
                self.template_var.get(),
                self.output_var.get(),
                rows,
                self.doi_var.get(),
            )

        except Exception as exc:
            self.status_var.set(
                f"Error: {exc}"
            )

            messagebox.showerror(
                "Form 22 Generator",
                str(exc),
            )

            return

        self.status_var.set(
            f"Completed: {self.output_var.get()}"
        )

        messagebox.showinfo(
            "Form 22 Generator",
            "The populated Form 22 was created successfully.",
        )


if __name__ == "__main__":
    Form22App().mainloop()
