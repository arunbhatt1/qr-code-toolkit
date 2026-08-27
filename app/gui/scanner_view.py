"""Comprehensive QR Scanner View with File Upload, Screen Snip, and Live Camera."""

from __future__ import annotations

import csv
import datetime
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog
from typing import Callable, List, Optional

import customtkinter as ctk
import cv2
from PIL import Image, ImageTk

from app.gui.components import StatusBadge
from app.scanner import DecodedQRResult, LiveCameraScanner, QRScanner


class ScannerView(ctk.CTkFrame):
    """Integrated QR Scanner view supporting files, clipboard, screen, and live camera feed."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_toast: Optional[Callable[[str, str], None]] = None,
        on_send_to_generator: Optional[Callable[[DecodedQRResult], None]] = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.on_toast = on_toast
        self.on_send_to_generator = on_send_to_generator

        self.scanner = QRScanner()
        self.camera_scanner = LiveCameraScanner()
        self.scan_history: List[dict] = []
        self.current_result: Optional[DecodedQRResult] = None
        self._cam_loop_id: Optional[str] = None
        self._cam_ctk_img: Optional[ctk.CTkImage] = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Create two-column scanner layout: Controls/Video on left, Results/History on right."""
        self.grid_columnconfigure(0, weight=1, minsize=420)
        self.grid_columnconfigure(1, weight=1, minsize=420)
        self.grid_rowconfigure(0, weight=1)

        # Left Column: Scan Source Selector (Image / Screen / Webcam)
        self.left_col = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=12)
        self.left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=0)
        self._build_source_tabs()

        # Right Column: Decoded Payload Inspector & History
        self.right_col = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.right_col.grid(row=0, column=1, sticky="nsew", padx=(12, 0), pady=0)
        self._build_result_inspector()
        self._build_history_section()

    def _build_source_tabs(self) -> None:
        """Tabs for File/Clipboard scanning vs Live Camera."""
        self.source_tabs = ctk.CTkTabview(self.left_col, command=self._on_source_tab_changed)
        self.source_tabs.pack(fill="both", expand=True, padx=12, pady=12)

        self.source_tabs.add("📂 Image & Screen")
        self.source_tabs.add("📹 Live Webcam")

        self._build_image_tab(self.source_tabs.tab("📂 Image & Screen"))
        self._build_webcam_tab(self.source_tabs.tab("📹 Live Webcam"))

    def _build_image_tab(self, tab: ctk.CTkFrame) -> None:
        """File upload, clipboard paste, and screen snip controls."""
        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(8, 12))
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        self.btn_open_file = ctk.CTkButton(
            btn_frame,
            text="📁 Browse Image...",
            fg_color="#0284C7",
            hover_color="#0369A1",
            height=36,
            command=self._scan_file,
        )
        self.btn_open_file.grid(row=0, column=0, sticky="ew", padx=4, pady=4)

        self.btn_paste_clip = ctk.CTkButton(
            btn_frame,
            text="📋 Paste Clipboard",
            fg_color="#334155",
            hover_color="#475569",
            height=36,
            command=self._scan_clipboard,
        )
        self.btn_paste_clip.grid(row=0, column=1, sticky="ew", padx=4, pady=4)

        self.btn_screen_snip = ctk.CTkButton(
            btn_frame,
            text="🖥️ Capture Entire Screen",
            fg_color="#334155",
            hover_color="#475569",
            height=36,
            command=self._scan_screen,
        )
        self.btn_screen_snip.grid(row=1, column=0, columnspan=2, sticky="ew", padx=4, pady=4)

        # Image preview box
        self.image_preview_box = ctk.CTkFrame(
            tab,
            fg_color="#0F172A",
            corner_radius=8,
            border_width=1,
            border_color="#334155",
            height=280,
        )
        self.image_preview_box.pack(fill="both", expand=True, padx=4, pady=(4, 8))

        self.image_preview_lbl = ctk.CTkLabel(
            self.image_preview_box,
            text="Select an image file or paste from clipboard\nto scan for QR codes.",
            text_color="#64748B",
        )
        self.image_preview_lbl.pack(expand=True, padx=20, pady=20)

    def _build_webcam_tab(self, tab: ctk.CTkFrame) -> None:
        """Live video stream with camera picker and start/stop."""
        cam_ctrls = ctk.CTkFrame(tab, fg_color="transparent")
        cam_ctrls.pack(fill="x", pady=(4, 8))

        ctk.CTkLabel(cam_ctrls, text="Webcam:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 6))

        cams = LiveCameraScanner.list_available_cameras()
        cam_labels = [f"Camera {i}" for i in cams]
        self.cam_var = tk.StringVar(value=cam_labels[0] if cam_labels else "No Camera")

        self.cam_menu = ctk.CTkOptionMenu(
            cam_ctrls,
            values=cam_labels if cam_labels else ["Camera 0"],
            variable=self.cam_var,
            width=130,
        )
        self.cam_menu.pack(side="left", padx=(0, 8))

        self.btn_cam_toggle = ctk.CTkButton(
            cam_ctrls,
            text="▶ Start Feed",
            fg_color="#059669",
            hover_color="#047857",
            width=100,
            command=self._toggle_webcam,
        )
        self.btn_cam_toggle.pack(side="right")

        # Camera Viewport Box
        self.cam_viewport = ctk.CTkFrame(
            tab,
            fg_color="#0F172A",
            corner_radius=8,
            border_width=1,
            border_color="#334155",
            height=280,
        )
        self.cam_viewport.pack(fill="both", expand=True, padx=4, pady=(4, 8))

        self.cam_view_lbl = ctk.CTkLabel(
            self.cam_viewport,
            text="Camera feed stopped.\nClick 'Start Feed' to begin scanning.",
            text_color="#64748B",
        )
        self.cam_view_lbl.pack(expand=True)

    # --- Right Column: Result Inspector & History ---

    def _build_result_inspector(self) -> None:
        """Structured card for the currently scanned QR code."""
        self.inspector_card = ctk.CTkFrame(self.right_col, fg_color="#1E293B", corner_radius=12)
        self.inspector_card.pack(fill="x", pady=(0, 16))

        top_row = ctk.CTkFrame(self.inspector_card, fg_color="transparent")
        top_row.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(
            top_row,
            text="Decoded QR Result",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(side="left")

        self.type_badge = ctk.CTkLabel(
            top_row,
            text="NO SCAN",
            fg_color="#334155",
            text_color="#94A3B8",
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            padx=8,
            pady=2,
        )
        self.type_badge.pack(side="right")

        # Parsed Details Container
        self.details_container = ctk.CTkFrame(self.inspector_card, fg_color="transparent")
        self.details_container.pack(fill="x", padx=16, pady=(0, 10))

        self.empty_prompt = ctk.CTkLabel(
            self.details_container,
            text="No QR code scanned yet.\nScan an image, screen region, or live camera.",
            text_color="#64748B",
            pady=20,
        )
        self.empty_prompt.pack()

        # Dynamic Action Buttons Frame
        self.action_btns_frame = ctk.CTkFrame(self.inspector_card, fg_color="transparent")
        self.action_btns_frame.pack(fill="x", padx=16, pady=(0, 16))

    def _build_history_section(self) -> None:
        """Recent scan history log."""
        hist_card = ctk.CTkFrame(self.right_col, fg_color="#1E293B", corner_radius=12)
        hist_card.pack(fill="x", pady=(0, 16))

        h_top = ctk.CTkFrame(hist_card, fg_color="transparent")
        h_top.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(h_top, text="Scan History", font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")

        self.btn_export_hist = ctk.CTkButton(
            h_top,
            text="Export CSV",
            width=80,
            height=26,
            fg_color="#334155",
            hover_color="#475569",
            command=self._export_history_csv,
        )
        self.btn_export_hist.pack(side="right", padx=(4, 0))

        self.btn_clear_hist = ctk.CTkButton(
            h_top,
            text="Clear",
            width=60,
            height=26,
            fg_color="#334155",
            hover_color="#475569",
            command=self._clear_history,
        )
        self.btn_clear_hist.pack(side="right")

        self.history_list_frame = ctk.CTkFrame(hist_card, fg_color="transparent")
        self.history_list_frame.pack(fill="x", padx=16, pady=(0, 16))

        self.hist_empty_lbl = ctk.CTkLabel(
            self.history_list_frame,
            text="Scan history is empty.",
            text_color="#64748B",
            pady=10,
        )
        self.hist_empty_lbl.pack()

    # --- Scanning Actions ---

    def _scan_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select QR Code Image",
            filetypes=[
                ("Image Files", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tiff;*.gif"),
                ("All Files", "*.*"),
            ],
        )
        if not path:
            return

        try:
            results = self.scanner.scan_image(path)
            # Display image in preview box
            with Image.open(path) as img:
                disp_img = img.copy()
                disp_img.thumbnail((300, 240))
                ctk_img = ctk.CTkImage(light_image=disp_img, dark_image=disp_img, size=disp_img.size)
                self.image_preview_lbl.configure(image=ctk_img, text="")

            self._handle_scan_results(results, source=Path(path).name)
        except Exception as exc:
            if self.on_toast:
                self.on_toast(f"Scan error: {str(exc)}", "error")

    def _scan_clipboard(self) -> None:
        try:
            results = self.scanner.scan_clipboard()
            if results:
                self._handle_scan_results(results, source="Clipboard")
            else:
                if self.on_toast:
                    self.on_toast("No QR code found in clipboard image.", "warning")
        except Exception as exc:
            if self.on_toast:
                self.on_toast(f"Clipboard scan failed: {str(exc)}", "error")

    def _scan_screen(self) -> None:
        try:
            results = self.scanner.scan_screen()
            if results:
                self._handle_scan_results(results, source="Screen Capture")
            else:
                if self.on_toast:
                    self.on_toast("No QR code detected on current screen.", "warning")
        except Exception as exc:
            if self.on_toast:
                self.on_toast(f"Screen scan failed: {str(exc)}", "error")

    def _toggle_webcam(self) -> None:
        if self.camera_scanner.is_running:
            self._stop_webcam()
        else:
            self._start_webcam()

    def _start_webcam(self) -> None:
        cam_idx = 0
        try:
            cam_str = self.cam_var.get()
            cam_idx = int(cam_str.split()[1])
        except Exception:
            pass

        ok = self.camera_scanner.start(cam_idx)
        if ok:
            self.btn_cam_toggle.configure(text="⏹ Stop Feed", fg_color="#DC2626", hover_color="#B91C1C")
            self._update_camera_frame()
            if self.on_toast:
                self.on_toast("Webcam feed active.", "info")
        else:
            if self.on_toast:
                self.on_toast("Failed to access selected webcam.", "error")

    def _stop_webcam(self) -> None:
        if self._cam_loop_id:
            self.after_cancel(self._cam_loop_id)
            self._cam_loop_id = None
        self.camera_scanner.stop()
        self.btn_cam_toggle.configure(text="▶ Start Feed", fg_color="#059669", hover_color="#047857")
        self.cam_view_lbl.configure(image=None, text="Camera feed stopped.\nClick 'Start Feed' to begin scanning.")

    def _update_camera_frame(self) -> None:
        if not self.camera_scanner.is_running:
            return

        ret, frame, results = self.camera_scanner.read_frame()
        if ret and frame is not None:
            # Convert BGR OpenCV frame to RGB PIL Image
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_frame)
            pil_img.thumbnail((320, 240))
            self._cam_ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
            self.cam_view_lbl.configure(image=self._cam_ctk_img, text="")

            if results:
                self._handle_scan_results(results, source="Live Camera")

        # Keep streaming at ~30 FPS
        self._cam_loop_id = self.after(33, self._update_camera_frame)

    def _on_source_tab_changed(self) -> None:
        if self.source_tabs.get() != "📹 Live Webcam" and self.camera_scanner.is_running:
            self._stop_webcam()

    # --- Result Presentation & Actions ---

    def _handle_scan_results(self, results: List[DecodedQRResult], source: str = "Image") -> None:
        if not results:
            if self.on_toast:
                self.on_toast("No QR code detected in the provided image.", "warning")
            return

        res = results[0]
        self.current_result = res

        # Play sound or notify toast
        if self.on_toast:
            self.on_toast(f"QR Code detected ({res.qr_type.upper()})!", "success")

        # Update Inspector UI
        self._render_inspector_card(res)

        # Append to scan history
        hist_entry = {
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "type": res.qr_type.upper(),
            "preview": res.raw_text[:45] + ("..." if len(res.raw_text) > 45 else ""),
            "raw": res.raw_text,
            "source": source,
        }
        self.scan_history.insert(0, hist_entry)
        self._render_history_list()

    def _render_inspector_card(self, res: DecodedQRResult) -> None:
        """Render detailed parsed attributes and contextual action buttons."""
        for widget in self.details_container.winfo_children():
            widget.destroy()
        for widget in self.action_btns_frame.winfo_children():
            widget.destroy()

        # Update Type Badge
        badge_colors = {
            "url": ("#065F46", "#34D399"),
            "wifi": ("#1E40AF", "#60A5FA"),
            "vcard": ("#5B21B6", "#C084FC"),
            "email": ("#854D0E", "#FACC15"),
            "phone": ("#065F46", "#34D399"),
            "sms": ("#9D174D", "#F472B6"),
            "location": ("#9A3412", "#FB923C"),
            "text": ("#334155", "#E2E8F0"),
        }
        bg, fg = badge_colors.get(res.qr_type, ("#334155", "#E2E8F0"))
        self.type_badge.configure(text=f" {res.qr_type.upper()} ", fg_color=bg, text_color=fg)

        # Attribute List
        data = res.parsed_data
        attr_grid = ctk.CTkFrame(self.details_container, fg_color="transparent")
        attr_grid.pack(fill="x", pady=4)
        attr_grid.grid_columnconfigure(1, weight=1)

        row_idx = 0
        for key, val in data.items():
            if not val or key == "maps_url":
                continue
            k_label = key.replace("_", " ").title() + ":"
            ctk.CTkLabel(
                attr_grid,
                text=k_label,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
            ).grid(row=row_idx, column=0, sticky="nw", padx=(0, 8), pady=2)

            val_str = str(val)
            val_entry = ctk.CTkEntry(attr_grid, height=28)
            val_entry.insert(0, val_str)
            val_entry.configure(state="readonly")
            val_entry.grid(row=row_idx, column=1, sticky="ew", pady=2)
            row_idx += 1

        # Raw Payload Textbox
        ctk.CTkLabel(
            self.details_container,
            text="Raw Payload:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#94A3B8",
            anchor="w",
        ).pack(fill="x", pady=(6, 2))

        raw_box = ctk.CTkTextbox(self.details_container, height=65)
        raw_box.insert("1.0", res.raw_text)
        raw_box.configure(state="disabled")
        raw_box.pack(fill="x", pady=(0, 6))

        # Contextual Action Buttons
        self.action_btns_frame.grid_columnconfigure((0, 1), weight=1)

        # Action 1: Contextual button
        if res.qr_type == "url":
            btn_act = ctk.CTkButton(
                self.action_btns_frame,
                text="🌐 Open in Browser",
                fg_color="#0284C7",
                hover_color="#0369A1",
                command=lambda: webbrowser.open(res.parsed_data.get("url", res.raw_text)),
            )
            btn_act.grid(row=0, column=0, sticky="ew", padx=3, pady=3)
        elif res.qr_type == "location":
            maps_u = res.parsed_data.get("maps_url", f"https://www.google.com/maps/search/?api=1&query={res.raw_text}")
            btn_act = ctk.CTkButton(
                self.action_btns_frame,
                text="🗺️ Open in Google Maps",
                fg_color="#0284C7",
                hover_color="#0369A1",
                command=lambda: webbrowser.open(maps_u),
            )
            btn_act.grid(row=0, column=0, sticky="ew", padx=3, pady=3)
        elif res.qr_type == "vCard":
            btn_act = ctk.CTkButton(
                self.action_btns_frame,
                text="👤 Save .vcf Contact",
                fg_color="#7C3AED",
                hover_color="#6D28D9",
                command=self._save_vcf_contact,
            )
            btn_act.grid(row=0, column=0, sticky="ew", padx=3, pady=3)
        elif res.qr_type == "wifi":
            btn_act = ctk.CTkButton(
                self.action_btns_frame,
                text="📋 Copy Wi-Fi Password",
                fg_color="#059669",
                hover_color="#047857",
                command=lambda: self._copy_text(res.parsed_data.get("password", ""), "Wi-Fi Password copied!"),
            )
            btn_act.grid(row=0, column=0, sticky="ew", padx=3, pady=3)
        else:
            btn_act = ctk.CTkButton(
                self.action_btns_frame,
                text="📋 Copy Raw Content",
                fg_color="#334155",
                hover_color="#475569",
                command=lambda: self._copy_text(res.raw_text, "Content copied to clipboard!"),
            )
            btn_act.grid(row=0, column=0, sticky="ew", padx=3, pady=3)

        # Action 2: Send to Generator
        if self.on_send_to_generator:
            btn_send = ctk.CTkButton(
                self.action_btns_frame,
                text="🎨 Send to Generator",
                fg_color="#6366F1",
                hover_color="#4F46E5",
                command=lambda: self.on_send_to_generator(res),
            )
            btn_send.grid(row=0, column=1, sticky="ew", padx=3, pady=3)

    def _render_history_list(self) -> None:
        """Render recent history item cards."""
        for widget in self.history_list_frame.winfo_children():
            widget.destroy()

        if not self.scan_history:
            self.hist_empty_lbl = ctk.CTkLabel(
                self.history_list_frame,
                text="Scan history is empty.",
                text_color="#64748B",
                pady=10,
            )
            self.hist_empty_lbl.pack()
            return

        for idx, item in enumerate(self.scan_history[:8]):
            card = ctk.CTkFrame(self.history_list_frame, fg_color="#0F172A", corner_radius=6)
            card.pack(fill="x", pady=2)

            t_lbl = ctk.CTkLabel(card, text=f"[{item['type']}]", font=ctk.CTkFont(size=11, weight="bold"), text_color="#38BDF8")
            t_lbl.pack(side="left", padx=(8, 4), pady=4)

            p_lbl = ctk.CTkLabel(card, text=item["preview"], font=ctk.CTkFont(size=11), anchor="w")
            p_lbl.pack(side="left", fill="x", expand=True, padx=4, pady=4)

            copy_btn = ctk.CTkButton(
                card,
                text="📋",
                width=26,
                height=22,
                fg_color="#334155",
                hover_color="#475569",
                command=lambda raw=item["raw"]: self._copy_text(raw, "Copied from history!"),
            )
            copy_btn.pack(side="right", padx=6, pady=4)

    def _copy_text(self, text: str, toast_msg: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        if self.on_toast:
            self.on_toast(toast_msg, "info")

    def _save_vcf_contact(self) -> None:
        if not self.current_result:
            return
        dest = filedialog.asksaveasfilename(
            title="Save Contact vCard",
            defaultextension=".vcf",
            initialfile="contact.vcf",
            filetypes=[("vCard Files", "*.vcf"), ("All Files", "*.*")],
        )
        if dest:
            Path(dest).write_text(self.current_result.raw_text, encoding="utf-8")
            if self.on_toast:
                self.on_toast("vCard contact saved successfully!", "success")

    def _clear_history(self) -> None:
        self.scan_history.clear()
        self._render_history_list()

    def _export_history_csv(self) -> None:
        if not self.scan_history:
            if self.on_toast:
                self.on_toast("History is empty.", "warning")
            return

        dest = filedialog.asksaveasfilename(
            title="Export History to CSV",
            defaultextension=".csv",
            initialfile="scan_history.csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
        )
        if not dest:
            return

        with open(dest, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["time", "type", "preview", "raw", "source"])
            writer.writeheader()
            writer.writerows(self.scan_history)

        if self.on_toast:
            self.on_toast(f"Exported {len(self.scan_history)} items to CSV.", "success")
