"""Tkinter window for the NC Form 22 Generator (offline)."""
from __future__ import annotations

import copy
import os
import subprocess
import sys
import tkinter as tk
from decimal import Decimal
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app_paths import default_output_dir  # noqa: E402
from form22_bridge import preview_reviewed, run_reviewed  # noqa: E402
from form22_version import APP_NAME, APP_VERSION, FORM_REVISION  # noqa: E402
from payroll_importer import import_payroll  # noqa: E402
from payroll_parser import form22_reporting_window, parse_amount, parse_iso_date  # noqa: E402
from pdf_payroll import extract_payroll_pdfs, mark_row_relationships, review_window_flags  # noqa: E402


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
        self.minsize(760, 560)
        self.payroll_paths: list[str] = []
        self.reviewed_rows: list[dict] | None = None
        self.doi = tk.StringVar()
        self.alt_template = tk.StringVar()
        self.last_output: Path | None = None
        self._build()

    def _build(self) -> None:
        frm = ttk.Frame(self, padding=16)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(0, weight=1)
        frm.rowconfigure(3, weight=1)
        ttk.Label(frm, text=APP_NAME, font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, sticky="w")
        ttk.Label(
            frm,
            text=f"Fills the official NC Industrial Commission Form 22 (rev. {FORM_REVISION}). "
                 "Works offline; payroll information stays on this computer.",
            wraplength=700,
        ).grid(row=1, column=0, sticky="w", pady=(0, 12))

        ttk.Label(frm, text="1. Add payroll records").grid(row=2, column=0, sticky="w")
        input_row = ttk.Frame(frm)
        input_row.grid(row=3, column=0, sticky="nsew")
        input_row.columnconfigure(0, weight=1)
        self.files = tk.Listbox(input_row, height=4, selectmode="extended", exportselection=False)
        self.files.grid(row=0, column=0, rowspan=3, sticky="nsew", padx=(0, 8))
        ttk.Button(input_row, text="Add Payroll PDF(s)...", command=self.pick_pdfs).grid(
            row=0, column=1, sticky="ew", pady=(0, 4))
        ttk.Button(input_row, text="Add CSV/JSON (advanced)...", command=self.pick_advanced).grid(
            row=1, column=1, sticky="ew", pady=4)
        ttk.Button(input_row, text="Remove selected", command=self.remove_files).grid(
            row=2, column=1, sticky="ew", pady=(4, 0))

        ttk.Label(frm, text="2. Enter or confirm the date of injury").grid(
            row=4, column=0, sticky="w", pady=(12, 0))
        doi_row = ttk.Frame(frm)
        doi_row.grid(row=5, column=0, sticky="ew")
        ttk.Label(doi_row, text="Date (YYYY-MM-DD):").pack(side="left")
        doi_entry = ttk.Entry(doi_row, textvariable=self.doi, width=18)
        doi_entry.pack(side="left", padx=8)
        doi_entry.bind("<KeyRelease>", self.on_doi_change)
        self.window_label = ttk.Label(doi_row, text="Reporting period: enter a valid injury date")
        self.window_label.pack(side="left", padx=6)

        ttk.Button(frm, text="3. Extract payroll for review", command=self.extract_and_review).grid(
            row=6, column=0, sticky="ew", pady=(12, 4))
        self.summary = tk.Text(frm, height=5, wrap="word", state="disabled", relief="flat",
                               background="#f3f3f3")
        self.summary.grid(row=7, column=0, sticky="nsew", pady=(4, 0))

        self.generate_btn = ttk.Button(frm, text="5. Generate Form 22", command=self.generate,
                                       state="disabled")
        self.generate_btn.grid(row=8, column=0, sticky="ew", pady=12)
        self.open_row = ttk.Frame(frm)
        self.open_row.grid(row=9, column=0, sticky="w")
        ttk.Button(self.open_row, text="Open completed PDF",
                   command=lambda: self.last_output and open_path(self.last_output)).pack(side="left")
        ttk.Button(self.open_row, text="Show in folder",
                   command=lambda: self.last_output and open_path(self.last_output, True)).pack(
                       side="left", padx=6)
        self.open_row.grid_remove()

        adv = ttk.LabelFrame(frm, text="Advanced", padding=8)
        adv.grid(row=10, column=0, sticky="ew", pady=(12, 0))
        adv.columnconfigure(0, weight=1)
        ttk.Label(adv, text="The bundled August 2026 Form 22 is the verified default. "
                  "Only choose another template if you know it is compatible.", wraplength=660).grid(
                      row=0, column=0, columnspan=3, sticky="w")
        ttk.Entry(adv, textvariable=self.alt_template).grid(row=1, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(adv, text="Browse...", command=self.pick_template).grid(row=1, column=1)
        ttk.Button(adv, text="Use default", command=lambda: self.alt_template.set("")).grid(
            row=1, column=2, padx=6)

    def _set_summary(self, text: str) -> None:
        self.summary.configure(state="normal")
        self.summary.delete("1.0", "end")
        self.summary.insert("1.0", text)
        self.summary.configure(state="disabled")

    def on_doi_change(self, _event=None) -> None:
        self.reviewed_rows = None
        self.generate_btn.configure(state="disabled")
        try:
            window = form22_reporting_window(self.doi.get().strip())
            self.window_label.configure(text=f"Reporting period: {window['start']} to {window['end']}")
        except ValueError:
            self.window_label.configure(text="Reporting period: enter a valid injury date")

    def _add_paths(self, paths: tuple[str, ...]) -> None:
        known = set(self.payroll_paths)
        for path in paths:
            if path not in known:
                self.payroll_paths.append(path)
                self.files.insert("end", Path(path).name)
                known.add(path)
        self.reviewed_rows = None
        self.generate_btn.configure(state="disabled")

    def pick_pdfs(self) -> None:
        chosen = filedialog.askopenfilenames(
            title="Select one or more payroll PDFs", filetypes=[("PDF payroll records", "*.pdf")])
        self._add_paths(chosen)

    def pick_advanced(self) -> None:
        chosen = filedialog.askopenfilenames(
            title="Select CSV or JSON payroll records",
            filetypes=[("CSV or JSON payroll", "*.csv *.json"), ("All files", "*.*")])
        self._add_paths(chosen)

    def remove_files(self) -> None:
        indexes = list(self.files.curselection())
        for index in reversed(indexes):
            self.files.delete(index)
            del self.payroll_paths[index]
        self.reviewed_rows = None
        self.generate_btn.configure(state="disabled")

    def pick_template(self) -> None:
        chosen = filedialog.askopenfilename(title="Select alternate Form 22 template",
                                            filetypes=[("PDF files", "*.pdf")])
        if chosen:
            self.alt_template.set(chosen)

    def extract_and_review(self) -> None:
        try:
            parse_iso_date(self.doi.get().strip(), "date of injury")
        except ValueError:
            messagebox.showerror(APP_NAME, "Enter a valid date of injury (YYYY-MM-DD) before extraction.")
            return
        rows: list[dict] = []
        issues: list[str] = []
        pdf_paths = [path for path in self.payroll_paths if Path(path).suffix.lower() == ".pdf"]
        other_paths = [path for path in self.payroll_paths if Path(path).suffix.lower() != ".pdf"]
        if pdf_paths:
            extracted = extract_payroll_pdfs(pdf_paths)
            rows.extend(extracted["rows"])
            issues.extend(extracted["issues"])
        for path in other_paths:
            try:
                for imported in import_payroll(path):
                    source = imported.get("source") or f"{Path(path).name}"
                    rows.append({
                        **imported,
                        "source": source,
                        "provenance": {"filename": Path(path).name, "page": None,
                                       "snippet": "Imported from CSV/JSON"},
                        "review_status": "Needs review",
                        "include": True,
                    })
            except (OSError, ValueError) as exc:
                issues.append(f"{Path(path).name}: {exc}")
        rows = review_window_flags(mark_row_relationships(rows), self.doi.get().strip())
        ReviewWindow(self, rows, issues)

    def accept_review(self, rows: list[dict], summary: str) -> None:
        self.reviewed_rows = copy.deepcopy(rows)
        self.generate_btn.configure(state="normal")
        self._set_summary(summary)

    def generate(self) -> None:
        self.open_row.grid_remove()
        if self.reviewed_rows is None:
            messagebox.showerror(APP_NAME, "Review payroll records before generating Form 22.")
            return
        default_name = f"Form22_{self.doi.get().strip()}.pdf"
        out = filedialog.asksaveasfilename(
            title="Save completed Form 22", defaultextension=".pdf", initialfile=default_name,
            initialdir=str(default_output_dir()), filetypes=[("PDF files", "*.pdf")])
        if not out:
            return
        if Path(out).resolve() in {Path(path).resolve() for path in self.payroll_paths}:
            messagebox.showerror(APP_NAME, "Choose a new file for Form 22; do not overwrite a payroll record.")
            return
        result = run_reviewed(self.reviewed_rows, self.doi.get(), out, self.alt_template.get() or None)
        if result["ok"]:
            self.last_output = Path(result["output"])
            self.open_row.grid()
            messagebox.showinfo(APP_NAME, "Your completed Form 22 was created.\n\n" + result["message"])
        else:
            messagebox.showerror(APP_NAME, result["message"])


class ReviewWindow(tk.Toplevel):
    COLUMNS = ("include", "date", "amount", "paid", "review", "source", "excerpt")

    def __init__(self, parent: App, rows: list[dict], issues: list[str]) -> None:
        super().__init__(parent)
        self.parent = parent
        self.rows = copy.deepcopy(rows)
        self.issues = issues
        self.title("4. Review payroll records")
        self.geometry("1000x560")
        self.transient(parent)
        self.grab_set()
        self._build()
        self.refresh()

    def _build(self) -> None:
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)
        try:
            window = form22_reporting_window(self.parent.doi.get().strip())
            period = f"Reporting period: {window['start']} through {window['end']} (injury date excluded)"
        except ValueError:
            period = "Enter a valid injury date before reviewing records."
        ttk.Label(frame, text=period, font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, sticky="w")
        self.notice = ttk.Label(frame, text="", wraplength=950, justify="left")
        self.notice.grid(row=1, column=0, sticky="ew", pady=6)
        table = ttk.Frame(frame)
        table.grid(row=2, column=0, sticky="nsew")
        table.columnconfigure(0, weight=1)
        table.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(table, columns=self.COLUMNS, show="headings", selectmode="browse")
        headings = {
            "include": "Include", "date": "Payroll date", "amount": "Earnings",
            "paid": "Paid in full?", "review": "Review flags", "source": "Source / page",
            "excerpt": "Source text",
        }
        widths = {"include": 65, "date": 110, "amount": 90, "paid": 100, "review": 190,
                  "source": 230, "excerpt": 280}
        for column in self.COLUMNS:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], stretch=column == "source")
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(table, orient="horizontal", command=self.tree.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.tag_configure("missing", background="#ffd9d9")
        self.tree.tag_configure("duplicate", background="#ffe6bf")
        self.tree.tag_configure("conflict", background="#fff2b3")
        self.tree.tag_configure("outside", foreground="#8b0000")
        buttons = ttk.Frame(frame)
        buttons.grid(row=3, column=0, sticky="ew", pady=8)
        for label, command in (
            ("Add manual row", self.add_row), ("Edit selected", self.edit_selected),
            ("Include / exclude", self.toggle_include), ("Delete selected", self.delete_selected),
        ):
            ttk.Button(buttons, text=label, command=command).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Accept reviewed rows", command=self.accept).pack(side="right")

    def refresh(self) -> None:
        self.rows = mark_row_relationships(self.rows)
        self.rows = review_window_flags(self.rows, self.parent.doi.get().strip())
        self.tree.delete(*self.tree.get_children())
        for index, row in enumerate(self.rows):
            date_text = str(row.get("date") or "Missing")
            amount = row.get("amount")
            amount_text = f"${Decimal(str(amount)):,.2f}" if amount is not None else "Missing"
            paid = row.get("paid_in_full")
            paid_text = "Yes" if paid is True else "No" if paid is False else "Needs review"
            flags = []
            tags = []
            if not row.get("date") or amount is None or paid is None:
                flags.append("Missing value")
                tags.append("missing")
            if row.get("duplicate"):
                flags.append(f"Possible duplicate of row {row.get('duplicate_of', '?') + 1}")
                tags.append("duplicate")
            if row.get("conflict"):
                flags.append("Different earnings on this date")
                tags.append("conflict")
            if row.get("period"):
                period = row["period"]
                flags.append(f"Pay period {period['start']} to {period['end']}")
            if row.get("outside_window"):
                flags.append("Outside reporting period")
                tags.append("outside")
            if not flags:
                flags.append("Needs review")
            provenance = row.get("provenance") or {}
            source = row.get("source") or provenance.get("filename") or "Manual entry"
            if provenance.get("page"):
                source += f", page {provenance['page']}"
            include = "Yes" if row.get("include", True) else "No"
            excerpt = (provenance.get("snippet") or "").strip()
            self.tree.insert("", "end", iid=str(index), values=(
                include, date_text, amount_text, paid_text, "; ".join(flags), source, excerpt,
            ), tags=tuple(tags))
        notes = list(self.issues)
        notes.append("Extracted values are candidates, not verified payroll facts. Correct each row, "
                     "choose Yes or No for paid-in-full, and exclude confirmed duplicates.")
        if not self.rows:
            notes.append("No rows were extracted. Add payroll rows manually to continue.")
        self.notice.configure(text="\n".join(notes))

    def add_row(self) -> None:
        self.edit_row({"date": "", "amount": None, "paid_in_full": None, "source": "Manual entry",
                       "provenance": {"filename": "Manual entry", "page": None, "snippet": ""},
                       "review_status": "Needs review", "include": True})

    def _selected_index(self) -> int | None:
        selected = self.tree.selection()
        return int(selected[0]) if selected else None

    def edit_selected(self) -> None:
        index = self._selected_index()
        if index is None:
            messagebox.showinfo(APP_NAME, "Select a payroll row to edit.")
            return
        self.edit_row(self.rows[index], index)

    def edit_row(self, row: dict, index: int | None = None) -> None:
        editor = tk.Toplevel(self)
        editor.title("Edit payroll row")
        editor.transient(self)
        editor.grab_set()
        frame = ttk.Frame(editor, padding=12)
        frame.pack(fill="both", expand=True)
        date_var = tk.StringVar(value=str(row.get("date") or ""))
        amount_var = tk.StringVar(value="" if row.get("amount") is None else str(row["amount"]))
        paid_value = row.get("paid_in_full")
        paid_var = tk.StringVar(value="Yes" if paid_value is True else "No" if paid_value is False else "")
        ttk.Label(frame, text="Payroll date (YYYY-MM-DD)").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=date_var, width=28).grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Label(frame, text="Earnings amount").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=amount_var, width=28).grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Label(frame, text="Was this day paid in full?").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Combobox(frame, textvariable=paid_var, values=("", "Yes", "No"), state="readonly").grid(
            row=2, column=1, sticky="ew", pady=4)
        ttk.Label(frame, text="Select Yes or No; blank means the row is not ready to accept.",
                  wraplength=300).grid(row=3, column=0, columnspan=2, sticky="w", pady=4)

        def save() -> None:
            try:
                work_date = parse_iso_date(date_var.get(), "payroll date").isoformat()
                amount = parse_amount(amount_var.get(), "earnings amount")
            except ValueError as exc:
                messagebox.showerror(APP_NAME, str(exc), parent=editor)
                return
            row["date"] = work_date
            row["amount"] = amount
            row["paid_in_full"] = True if paid_var.get() == "Yes" else False if paid_var.get() == "No" else None
            row["review_status"] = "Needs review"
            row["field_status"] = {"date": "Reviewed", "amount": "Reviewed",
                                   "paid_in_full": "Reviewed" if paid_var.get() else "Missing"}
            if index is None:
                self.rows.append(row)
            else:
                self.rows[index] = row
            editor.destroy()
            self.refresh()

        ttk.Button(frame, text="Save row", command=save).grid(row=4, column=0, columnspan=2, pady=(8, 0))

    def toggle_include(self) -> None:
        index = self._selected_index()
        if index is None:
            messagebox.showinfo(APP_NAME, "Select a payroll row.")
            return
        self.rows[index]["include"] = not self.rows[index].get("include", True)
        self.refresh()

    def delete_selected(self) -> None:
        index = self._selected_index()
        if index is not None:
            del self.rows[index]
            self.refresh()

    def accept(self) -> None:
        for row in self.rows:
            if row.get("include", True):
                row["review_status"] = "Reviewed"
        self.rows = mark_row_relationships(self.rows)
        result = preview_reviewed(self.rows, self.parent.doi.get().strip())
        if not result["ok"]:
            messagebox.showerror(APP_NAME, result["message"], parent=self)
            return
        conflicts = [row for row in self.rows if row.get("include", True) and row.get("conflict")]
        outside = [row for row in self.rows if row.get("include", True) and row.get("outside_window")]
        if conflicts and not messagebox.askyesno(
                APP_NAME, f"{len(conflicts)} selected row(s) have different earnings on the same date. "
                "Review these values carefully. Continue with all selected rows?", parent=self):
            return
        if outside and not messagebox.askyesno(
                APP_NAME, f"{len(outside)} selected row(s) are outside the reporting period and will not "
                "be included in Form 22. Continue?", parent=self):
            return
        self.parent.accept_review(self.rows, result["message"])
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
