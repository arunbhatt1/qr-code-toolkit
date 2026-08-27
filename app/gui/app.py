"""Main CustomTkinter desktop window and navigation architecture."""

from __future__ import annotations

import sys
import tkinter as tk
from typing import Dict, Optional

import customtkinter as ctk

from app import __version__
from app.gui.batch_view import BatchView
from app.gui.components import ToastNotification
from app.gui.generator_view import GeneratorView
from app.gui.scanner_view import ScannerView
from app.gui.settings_view import SettingsView
from app.scanner import DecodedQRResult


class QRCodeToolkitApp(ctk.CTk):
    """Main application root window with responsive sidebar navigation."""

    def __init__(self) -> None:
        super().__init__()

        # Appearance & Window Configuration
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title(f"QR Code Toolkit v{__version__} — Privacy-First Desktop Suite")
        self.geometry("1180x760")
        self.minsize(980, 620)

        # Main Layout Grid: Sidebar on left (col 0), Views container on right (col 1)
        self.grid_columnconfigure(0, weight=0, minsize=220)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.views: Dict[str, ctk.CTkFrame] = {}
        self.nav_buttons: Dict[str, ctk.CTkButton] = {}

        self._build_sidebar()
        self._build_views_container()

        # Default view: Generator
        self.show_view("generator")

    def _build_sidebar(self) -> None:
        """Create sleek navigation sidebar with icon buttons."""
        self.sidebar = ctk.CTkFrame(self, fg_color="#0F172A", corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(5, weight=1)  # Spacer push to bottom

        # App Brand Header
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.pack(fill="x", padx=16, pady=(24, 20))

        brand_title = ctk.CTkLabel(
            brand_frame,
            text="⚡ QR Toolkit",
            font=ctk.CTkFont(family="Inter", size=20, weight="bold"),
            text_color="#38BDF8",
            anchor="w",
        )
        brand_title.pack(fill="x")

        brand_sub = ctk.CTkLabel(
            brand_frame,
            text="Privacy-First Desktop Suite",
            font=ctk.CTkFont(size=11),
            text_color="#94A3B8",
            anchor="w",
        )
        brand_sub.pack(fill="x")

        # Navigation Buttons
        nav_items = [
            ("generator", "🎯 Single Generator", "#6366F1"),
            ("scanner", "📷 Scan & Camera", "#0284C7"),
            ("batch", "📦 Batch Studio", "#059669"),
            ("settings", "⚙️ Settings & Logs", "#64748B"),
        ]

        for view_key, label, active_color in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                anchor="w",
                font=ctk.CTkFont(size=13, weight="bold"),
                height=42,
                corner_radius=8,
                fg_color="transparent",
                hover_color="#1E293B",
                text_color="#E2E8F0",
                command=lambda k=view_key: self.show_view(k),
            )
            btn.pack(fill="x", padx=12, pady=4)
            self.nav_buttons[view_key] = btn

        # Bottom Status Area
        status_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        status_frame.pack(side="bottom", fill="x", padx=16, pady=16)

        offline_badge = ctk.CTkLabel(
            status_frame,
            text="🟢 100% Offline & Private",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#34D399",
            anchor="w",
        )
        offline_badge.pack(fill="x")

        ver_label = ctk.CTkLabel(
            status_frame,
            text=f"Version {__version__}",
            font=ctk.CTkFont(size=10),
            text_color="#64748B",
            anchor="w",
        )
        ver_label.pack(fill="x", pady=(2, 0))

    def _build_views_container(self) -> None:
        """Create container and initialize the 4 main application views."""
        self.container = ctk.CTkFrame(self, fg_color="#090D16", corner_radius=0)
        self.container.grid(row=0, column=1, sticky="nsew", padx=16, pady=16)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        # Initialize Views
        self.views["generator"] = GeneratorView(self.container, on_toast=self.show_toast)
        self.views["scanner"] = ScannerView(
            self.container,
            on_toast=self.show_toast,
            on_send_to_generator=self._handle_send_to_generator,
        )
        self.views["batch"] = BatchView(self.container, on_toast=self.show_toast)
        self.views["settings"] = SettingsView(self.container, on_toast=self.show_toast)

    def show_view(self, view_name: str) -> None:
        """Raise the selected view and update sidebar button highlight."""
        if view_name not in self.views:
            return

        # Hide all views
        for v in self.views.values():
            v.grid_forget()

        # Show target view
        target_view = self.views[view_name]
        target_view.grid(row=0, column=0, sticky="nsew")

        # Update button styles
        for k, btn in self.nav_buttons.items():
            if k == view_name:
                btn.configure(fg_color="#1E293B", text_color="#38BDF8")
            else:
                btn.configure(fg_color="transparent", text_color="#E2E8F0")

    def show_toast(self, message: str, toast_type: str = "info") -> None:
        """Display an animated floating toast notification."""
        ToastNotification(self, message=message, toast_type=toast_type)

    def _handle_send_to_generator(self, result: DecodedQRResult) -> None:
        """Transfer scanned QR data into Generator view and switch tabs."""
        gen_view: GeneratorView = self.views["generator"]  # type: ignore

        # Match type to tab
        type_to_tab = {
            "url": "URL",
            "text": "Text",
            "wifi": "Wi-Fi",
            "vcard": "vCard",
            "email": "Email",
            "phone": "Phone",
            "sms": "SMS",
            "location": "Location",
        }
        target_tab = type_to_tab.get(result.qr_type.lower(), "Text")
        gen_view.payload_tabview.set(target_tab)

        # Populate fields
        data = result.parsed_data
        if target_tab == "URL":
            gen_view.url_var.set(data.get("url", result.raw_text))
        elif target_tab == "Text":
            gen_view.text_box.delete("1.0", "end")
            gen_view.text_box.insert("1.0", data.get("text", result.raw_text))
        elif target_tab == "Wi-Fi":
            gen_view.wifi_ssid_var.set(data.get("ssid", ""))
            gen_view.wifi_pass_var.set(data.get("password", ""))
            gen_view.wifi_sec_var.set(data.get("security", "WPA"))
            gen_view.wifi_hidden_var.set(data.get("hidden", False))
        elif target_tab == "vCard":
            gen_view.vcard_name_var.set(data.get("name", ""))
            gen_view.vcard_org_var.set(data.get("org", ""))
            gen_view.vcard_phone_var.set(data.get("phone", ""))
            gen_view.vcard_email_var.set(data.get("email", ""))
            gen_view.vcard_web_var.set(data.get("website", ""))
            gen_view.vcard_addr_var.set(data.get("address", ""))
        elif target_tab == "Email":
            gen_view.email_to_var.set(data.get("email", ""))
            gen_view.email_sub_var.set(data.get("subject", ""))
            gen_view.email_body_box.delete("1.0", "end")
            gen_view.email_body_box.insert("1.0", data.get("body", ""))
        elif target_tab == "Phone":
            gen_view.phone_var.set(data.get("phone", result.raw_text))
        elif target_tab == "SMS":
            gen_view.sms_phone_var.set(data.get("phone", ""))
            gen_view.sms_msg_box.delete("1.0", "end")
            gen_view.sms_msg_box.insert("1.0", data.get("message", ""))
        elif target_tab == "Location":
            gen_view.loc_lat_var.set(str(data.get("latitude", "0.0")))
            gen_view.loc_lon_var.set(str(data.get("longitude", "0.0")))

        # Switch to Generator View
        self.show_view("generator")
        self.show_toast(f"Loaded decoded {result.qr_type.upper()} into Generator.", "info")


def run_app() -> None:
    """Launch the GUI application."""
    app = QRCodeToolkitApp()
    app.mainloop()
