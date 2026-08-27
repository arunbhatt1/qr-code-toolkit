"""Settings, Appearance, Privacy Log Viewer, and Diagnostics View."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

import customtkinter as ctk

from app import __version__
from app.logging_config import _LOG_FILE


class SettingsView(ctk.CTkFrame):
    """Application settings, theme customization, and privacy log viewer."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_toast: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.on_toast = on_toast
        self._build_ui()
        self._load_logs()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1, minsize=420)
        self.grid_columnconfigure(1, weight=1, minsize=420)
        self.grid_rowconfigure(0, weight=1)

        # Left Column: Appearance & Privacy Statement
        left_col = ctk.CTkScrollableFrame(self, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=0)

        # Appearance Card
        app_card = ctk.CTkFrame(left_col, fg_color="#1E293B", corner_radius=12)
        app_card.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(app_card, text="Appearance & Theme", font=ctk.CTkFont(size=16, weight="bold"), anchor="w").pack(fill="x", padx=16, pady=(16, 12))

        # Mode
        mode_frame = ctk.CTkFrame(app_card, fg_color="transparent")
        mode_frame.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(mode_frame, text="Interface Mode:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        self.mode_menu = ctk.CTkOptionMenu(
            mode_frame,
            values=["Dark", "Light", "System"],
            command=self._change_appearance_mode,
            width=130,
        )
        self.mode_menu.set("Dark")
        self.mode_menu.pack(side="right")

        # Privacy Card
        priv_card = ctk.CTkFrame(left_col, fg_color="#1E293B", corner_radius=12)
        priv_card.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(priv_card, text="🔒 Privacy & Security Guarantee", font=ctk.CTkFont(size=16, weight="bold"), anchor="w").pack(fill="x", padx=16, pady=(16, 8))

        privacy_bullets = [
            "• 100% Offline: Zero internet access or background telemetry.",
            "• Zero Secret Logging: Wi-Fi passwords and contacts are never written to logs.",
            "• Local-Only Processing: Generation and computer-vision scanning run entirely on your CPU.",
            "• Standalone: No third-party accounts or cloud APIs required.",
        ]
        for bullet in privacy_bullets:
            ctk.CTkLabel(
                priv_card,
                text=bullet,
                font=ctk.CTkFont(size=12),
                text_color="#94A3B8",
                anchor="w",
                justify="left",
            ).pack(fill="x", padx=16, pady=2)

        ctk.CTkLabel(priv_card, text="", height=8).pack()

        # System Info Card
        sys_card = ctk.CTkFrame(left_col, fg_color="#1E293B", corner_radius=12)
        sys_card.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(sys_card, text="System Diagnostics", font=ctk.CTkFont(size=16, weight="bold"), anchor="w").pack(fill="x", padx=16, pady=(16, 8))

        import importlib.metadata
        import cv2
        import PIL

        def get_ver(pkg: str, default: str = "Installed") -> str:
            try:
                return importlib.metadata.version(pkg)
            except Exception:
                return default

        info_rows = [
            ("App Version", f"v{__version__}"),
            ("Python", sys.version.split()[0]),
            ("OpenCV", cv2.__version__),
            ("Pillow", PIL.__version__),
            ("qrcode Engine", f"v{get_ver('qrcode')}"),
        ]
        for label_t, val_t in info_rows:
            row_f = ctk.CTkFrame(sys_card, fg_color="transparent")
            row_f.pack(fill="x", padx=16, pady=2)
            ctk.CTkLabel(row_f, text=label_t, font=ctk.CTkFont(size=11, weight="bold"), text_color="#94A3B8").pack(side="left")
            ctk.CTkLabel(row_f, text=val_t, font=ctk.CTkFont(size=11)).pack(side="right")

        ctk.CTkLabel(sys_card, text="", height=8).pack()

        # Right Column: Sanitized Local Log Viewer
        right_col = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=12)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(12, 0), pady=0)

        log_header = ctk.CTkFrame(right_col, fg_color="transparent")
        log_header.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(log_header, text="Sanitized Local Logs", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

        self.btn_open_dir = ctk.CTkButton(
            log_header,
            text="Open Folder",
            width=90,
            height=26,
            fg_color="#334155",
            hover_color="#475569",
            command=self._open_log_folder,
        )
        self.btn_open_dir.pack(side="right", padx=(4, 0))

        self.btn_clear_log = ctk.CTkButton(
            log_header,
            text="Clear",
            width=60,
            height=26,
            fg_color="#334155",
            hover_color="#475569",
            command=self._clear_logs,
        )
        self.btn_clear_log.pack(side="right", padx=(4, 0))

        self.btn_refresh_log = ctk.CTkButton(
            log_header,
            text="🔄 Refresh",
            width=80,
            height=26,
            fg_color="#0284C7",
            hover_color="#0369A1",
            command=self._load_logs,
        )
        self.btn_refresh_log.pack(side="right")

        self.log_textbox = ctk.CTkTextbox(
            right_col,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#0F172A",
        )
        self.log_textbox.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    def _change_appearance_mode(self, new_mode: str) -> None:
        ctk.set_appearance_mode(new_mode.lower())
        if self.on_toast:
            self.on_toast(f"Switched theme to {new_mode}.", "info")

    def _load_logs(self) -> None:
        self.log_textbox.delete("1.0", "end")
        if _LOG_FILE.exists():
            try:
                content = _LOG_FILE.read_text(encoding="utf-8")
                # Show last 200 lines
                lines = content.splitlines()[-200:]
                self.log_textbox.insert("1.0", "\n".join(lines))
            except Exception as exc:
                self.log_textbox.insert("1.0", f"Error reading log file: {str(exc)}")
        else:
            self.log_textbox.insert("1.0", "Log file is currently empty.")

    def _clear_logs(self) -> None:
        if _LOG_FILE.exists():
            try:
                _LOG_FILE.write_text("", encoding="utf-8")
                self._load_logs()
                if self.on_toast:
                    self.on_toast("Local log cleared.", "info")
            except Exception as exc:
                if self.on_toast:
                    self.on_toast(f"Failed to clear log: {str(exc)}", "error")

    def _open_log_folder(self) -> None:
        folder = _LOG_FILE.parent.resolve()
        folder.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(folder))
        else:
            subprocess.Popen(["xdg-open", str(folder)])
