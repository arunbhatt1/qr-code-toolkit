"""Batch QR Code Generation View for Bulk CSV and TXT Processing."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Callable, Dict, List, Optional

import customtkinter as ctk

from app.batch import BatchGenerator, BatchItem
from app.gui.components import StatusBadge
from app.styling import QRStyleConfig


class BatchView(ctk.CTkFrame):
    """Batch generation view for bulk CSV / TXT to QR codes."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_toast: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.on_toast = on_toast
        self.batch_engine = BatchGenerator()
        self.csv_headers: List[str] = []
        self.csv_rows: List[Dict[str, str]] = []
        self.loaded_lines: List[str] = []
        self.is_processing = False
        self._cancel_requested = False

        self._build_ui()

    def _build_ui(self) -> None:
        """Create the batch generation layout."""
        self.grid_columnconfigure(0, weight=1, minsize=420)
        self.grid_columnconfigure(1, weight=1, minsize=420)
        self.grid_rowconfigure(0, weight=1)

        # Left Column: Source Upload, Columns, and Templates
        self.left_col = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=0)
        self._build_source_card()
        self._build_template_card()

        # Right Column: Output Config, Progress & Job Log
        self.right_col = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=12)
        self.right_col.grid(row=0, column=1, sticky="nsew", padx=(12, 0), pady=0)
        self._build_output_card()
        self._build_progress_card()

    def _build_source_card(self) -> None:
        """Data source import section."""
        card = ctk.CTkFrame(self.left_col, fg_color="#1E293B", corner_radius=12)
        card.pack(fill="x", pady=(0, 16))

        header = ctk.CTkLabel(card, text="1. Select Data Source", font=ctk.CTkFont(size=16, weight="bold"), anchor="w")
        header.pack(fill="x", padx=16, pady=(16, 8))

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 10))
        btn_row.grid_columnconfigure((0, 1), weight=1)

        self.btn_import_csv = ctk.CTkButton(
            btn_row,
            text="📊 Import CSV File...",
            fg_color="#0284C7",
            hover_color="#0369A1",
            command=self._import_csv,
        )
        self.btn_import_csv.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.btn_import_txt = ctk.CTkButton(
            btn_row,
            text="📄 Import TXT Lines...",
            fg_color="#334155",
            hover_color="#475569",
            command=self._import_txt,
        )
        self.btn_import_txt.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        self.file_info_lbl = ctk.CTkLabel(
            card,
            text="No file loaded. Import a CSV or TXT file to start.",
            text_color="#94A3B8",
            anchor="w",
        )
        self.file_info_lbl.pack(fill="x", padx=16, pady=(0, 8))

        # Detected Columns Chips
        self.chips_container = ctk.CTkFrame(card, fg_color="transparent")
        self.chips_container.pack(fill="x", padx=16, pady=(0, 16))

    def _build_template_card(self) -> None:
        """Template string builder."""
        card = ctk.CTkFrame(self.left_col, fg_color="#1E293B", corner_radius=12)
        card.pack(fill="x", pady=(0, 16))

        header = ctk.CTkLabel(card, text="2. Configure Templates", font=ctk.CTkFont(size=16, weight="bold"), anchor="w")
        header.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(
            card,
            text="QR Payload Template (use {column_name} placeholders):",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 2))

        self.payload_tmpl_var = tk.StringVar(value="{url}")
        self.payload_tmpl_entry = ctk.CTkEntry(card, textvariable=self.payload_tmpl_var)
        self.payload_tmpl_entry.pack(fill="x", padx=16, pady=(0, 10))

        ctk.CTkLabel(
            card,
            text="Filename Template:",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 2))

        self.fn_tmpl_var = tk.StringVar(value="qr_{index}")
        self.fn_tmpl_entry = ctk.CTkEntry(card, textvariable=self.fn_tmpl_var)
        self.fn_tmpl_entry.pack(fill="x", padx=16, pady=(0, 16))

    def _build_output_card(self) -> None:
        """Export destination and format selection."""
        header = ctk.CTkLabel(self.right_col, text="3. Output & Export Settings", font=ctk.CTkFont(size=16, weight="bold"), anchor="w")
        header.pack(fill="x", padx=20, pady=(20, 8))

        # Output folder picker
        folder_frame = ctk.CTkFrame(self.right_col, fg_color="transparent")
        folder_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.output_dir_var = tk.StringVar(value=str(Path.home() / "Documents" / "QR_Exports"))
        self.output_dir_entry = ctk.CTkEntry(folder_frame, textvariable=self.output_dir_var)
        self.output_dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_browse_out = ctk.CTkButton(folder_frame, text="Browse...", width=90, command=self._browse_output_dir)
        btn_browse_out.pack(side="right")

        # Format & Zip options
        opt_frame = ctk.CTkFrame(self.right_col, fg_color="transparent")
        opt_frame.pack(fill="x", padx=20, pady=(0, 16))
        opt_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(opt_frame, text="Format:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").grid(row=0, column=0, sticky="w", padx=2)
        self.fmt_var = tk.StringVar(value="PNG")
        self.fmt_menu = ctk.CTkOptionMenu(opt_frame, values=["PNG", "JPG", "SVG", "PDF"], variable=self.fmt_var)
        self.fmt_menu.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(2, 0))

        self.zip_var = tk.BooleanVar(value=False)
        self.zip_chk = ctk.CTkCheckBox(opt_frame, text="Package into .ZIP file", variable=self.zip_var)
        self.zip_chk.grid(row=1, column=1, sticky="w", padx=(6, 0), pady=(2, 0))

    def _build_progress_card(self) -> None:
        """Batch progress bar, action buttons, and live log."""
        prog_header = ctk.CTkFrame(self.right_col, fg_color="transparent")
        prog_header.pack(fill="x", padx=20, pady=(0, 8))

        ctk.CTkLabel(prog_header, text="Generation Progress", font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")

        self.prog_pct_lbl = ctk.CTkLabel(prog_header, text="0%", font=ctk.CTkFont(size=13, weight="bold"), text_color="#38BDF8")
        self.prog_pct_lbl.pack(side="right")

        self.prog_bar = ctk.CTkProgressBar(self.right_col)
        self.prog_bar.set(0.0)
        self.prog_bar.pack(fill="x", padx=20, pady=(0, 8))

        self.status_msg_lbl = ctk.CTkLabel(
            self.right_col,
            text="Ready to generate.",
            text_color="#94A3B8",
            anchor="w",
        )
        self.status_msg_lbl.pack(fill="x", padx=20, pady=(0, 12))

        # Control Buttons
        ctrl_frame = ctk.CTkFrame(self.right_col, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=20, pady=(0, 16))
        ctrl_frame.grid_columnconfigure((0, 1), weight=1)

        self.btn_start = ctk.CTkButton(
            ctrl_frame,
            text="🚀 Start Batch Generation",
            fg_color="#059669",
            hover_color="#047857",
            height=36,
            command=self._start_batch_thread,
        )
        self.btn_start.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.btn_cancel = ctk.CTkButton(
            ctrl_frame,
            text="⏹ Cancel",
            fg_color="#334155",
            hover_color="#475569",
            height=36,
            state="disabled",
            command=self._cancel_batch,
        )
        self.btn_cancel.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        # Log Table of Results
        ctk.CTkLabel(self.right_col, text="Generated Files Log:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x", padx=20, pady=(0, 4))

        self.log_scroll = ctk.CTkScrollableFrame(self.right_col, fg_color="#0F172A", height=140)
        self.log_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    # --- Source Handlers ---

    def _import_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
        )
        if not path:
            return

        try:
            headers, rows = BatchGenerator.parse_csv_file(path)
            self.csv_headers = headers
            self.csv_rows = rows
            self.loaded_lines = []

            self.file_info_lbl.configure(
                text=f"Loaded CSV: {Path(path).name} ({len(rows)} records, {len(headers)} columns)",
                text_color="#34D399",
            )
            self._render_column_chips(headers)

            if headers:
                first_col = headers[0]
                self.payload_tmpl_var.set(f"{{{first_col}}}")
                self.fn_tmpl_var.set(f"qr_{{{first_col}}}")

            if self.on_toast:
                self.on_toast(f"Imported {len(rows)} records from CSV.", "success")
        except Exception as exc:
            if self.on_toast:
                self.on_toast(f"CSV import error: {str(exc)}", "error")

    def _import_txt(self) -> None:
        path = filedialog.askopenfilename(
            title="Select TXT File",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if not path:
            return

        try:
            lines = BatchGenerator.parse_text_lines(path)
            self.loaded_lines = lines
            self.csv_headers = []
            self.csv_rows = []

            self.file_info_lbl.configure(
                text=f"Loaded Text: {Path(path).name} ({len(lines)} lines)",
                text_color="#34D399",
            )
            self._render_column_chips([])
            self.payload_tmpl_var.set("{line}")
            self.fn_tmpl_var.set("qr_{index}")

            if self.on_toast:
                self.on_toast(f"Imported {len(lines)} lines.", "success")
        except Exception as exc:
            if self.on_toast:
                self.on_toast(f"TXT import error: {str(exc)}", "error")

    def _render_column_chips(self, headers: List[str]) -> None:
        for widget in self.chips_container.winfo_children():
            widget.destroy()

        if not headers:
            return

        ctk.CTkLabel(self.chips_container, text="Click column tag to insert:", font=ctk.CTkFont(size=11), text_color="#94A3B8").pack(anchor="w", pady=(0, 4))
        chip_frame = ctk.CTkFrame(self.chips_container, fg_color="transparent")
        chip_frame.pack(fill="x")

        for h in headers:
            btn = ctk.CTkButton(
                chip_frame,
                text=f"{{{h}}}",
                width=60,
                height=24,
                fg_color="#334155",
                hover_color="#475569",
                font=ctk.CTkFont(size=11),
                command=lambda tag=h: self._insert_tag(tag),
            )
            btn.pack(side="left", padx=2, pady=2)

    def _insert_tag(self, tag: str) -> None:
        current = self.payload_tmpl_var.get()
        self.payload_tmpl_var.set(f"{current}{{{tag}}}")

    def _browse_output_dir(self) -> None:
        dir_p = filedialog.askdirectory(title="Select Output Folder")
        if dir_p:
            self.output_dir_var.set(dir_p)

    # --- Execution & Threading ---

    def _start_batch_thread(self) -> None:
        if not self.csv_rows and not self.loaded_lines:
            if self.on_toast:
                self.on_toast("Please import a CSV or TXT file first.", "warning")
            return

        out_dir = Path(self.output_dir_var.get().strip())
        if not out_dir:
            if self.on_toast:
                self.on_toast("Please specify an output directory.", "warning")
            return

        # Prepare Batch Items
        if self.csv_rows:
            items = BatchGenerator.build_items_from_csv(
                self.csv_rows,
                payload_template=self.payload_tmpl_var.get(),
                filename_template=self.fn_tmpl_var.get(),
            )
        else:
            items = BatchGenerator.build_items_from_lines(
                self.loaded_lines,
                filename_prefix=self.fn_tmpl_var.get().replace("{index}", "").strip("_") or "qr",
            )

        if not items:
            if self.on_toast:
                self.on_toast("No items to generate.", "warning")
            return

        # Reset UI
        for widget in self.log_scroll.winfo_children():
            widget.destroy()

        self.is_processing = True
        self._cancel_requested = False
        self.btn_start.configure(state="disabled")
        self.btn_cancel.configure(state="normal", fg_color="#DC2626", hover_color="#B91C1C")
        self.prog_bar.set(0.0)
        self.prog_pct_lbl.configure(text="0%")
        self.status_msg_lbl.configure(text=f"Starting batch of {len(items)} items...")

        # Run batch generation on worker thread to keep GUI responsive
        threading.Thread(
            target=self._run_batch_worker,
            args=(items, out_dir, self.fmt_var.get(), self.zip_var.get()),
            daemon=True,
        ).start()

    def _run_batch_worker(
        self,
        items: List[BatchItem],
        out_dir: Path,
        fmt: str,
        create_zip: bool,
    ) -> None:
        total = len(items)

        def progress_cb(cur: int, tot: int, item: BatchItem) -> None:
            self.after(0, self._update_item_progress, cur, tot, item)

        def cancel_check() -> bool:
            return self._cancel_requested

        processed_items = self.batch_engine.process_batch(
            items=items,
            output_directory=out_dir,
            file_format=fmt,
            progress_callback=progress_cb,
            cancel_check=cancel_check,
        )

        zip_p = None
        if create_zip and not self._cancel_requested:
            zip_p = out_dir / f"batch_qr_export_{fmt.lower()}.zip"
            BatchGenerator.create_zip_archive(out_dir, zip_p)

        self.after(0, self._batch_finished, processed_items, zip_p)

    def _update_item_progress(self, cur: int, total: int, item: BatchItem) -> None:
        pct = (cur / total) if total > 0 else 1.0
        self.prog_bar.set(pct)
        self.prog_pct_lbl.configure(text=f"{int(pct * 100)}%")
        self.status_msg_lbl.configure(text=f"Processed item {cur} of {total} ({item.filename})")

        # Append to log list (keep last 20)
        row = ctk.CTkFrame(self.log_scroll, fg_color="transparent")
        row.pack(fill="x", pady=1)

        ctk.CTkLabel(row, text=f"#{item.index}", font=ctk.CTkFont(size=11), width=35).pack(side="left")
        ctk.CTkLabel(row, text=item.filename, font=ctk.CTkFont(size=11, weight="bold"), anchor="w").pack(side="left", fill="x", expand=True, padx=4)

        badge = StatusBadge(row, item.status)
        badge.pack(side="right")

    def _cancel_batch(self) -> None:
        self._cancel_requested = True
        self.status_msg_lbl.configure(text="Cancelling batch generation...")

    def _batch_finished(self, items: List[BatchItem], zip_path: Optional[Path]) -> None:
        self.is_processing = False
        self.btn_start.configure(state="normal")
        self.btn_cancel.configure(state="disabled", fg_color="#334155")

        success_cnt = sum(1 for i in items if i.status == "success")
        if self._cancel_requested:
            msg = f"Batch cancelled. Generated {success_cnt} of {len(items)} QR codes."
            self.status_msg_lbl.configure(text=msg, text_color="#FBBF24")
            if self.on_toast:
                self.on_toast(msg, "warning")
        else:
            msg = f"Batch complete! Generated {success_cnt} QR codes successfully."
            self.status_msg_lbl.configure(text=msg, text_color="#34D399")
            if self.on_toast:
                self.on_toast(msg, "success")
