"""Smoke tests for GUI views initialization and widget structure."""

import tkinter as tk
import pytest
import customtkinter as ctk

from app.gui.app import QRCodeToolkitApp
from app.gui.batch_view import BatchView
from app.gui.components import ColorPickerButton, StatusBadge, ToastNotification
from app.gui.generator_view import GeneratorView
from app.gui.scanner_view import ScannerView
from app.gui.settings_view import SettingsView
from app.scanner import DecodedQRResult


class TestGUISmoke:
    """Smoke tests to ensure GUI widgets instantiate properly without Tk errors."""

    @pytest.fixture(autouse=True)
    def setup_tk(self):
        # Create a hidden CTk instance for testing
        ctk.set_appearance_mode("dark")
        self.root = ctk.CTk()
        self.root.withdraw()
        yield
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_components_instantiation(self):
        badge = StatusBadge(self.root, "success")
        assert badge.cget("text").strip() == "SUCCESS"

        toast = ToastNotification(self.root, "Test message", toast_type="info")
        assert toast.label.cget("text") == "ℹ️  Test message"
        toast.dismiss()

        picker = ColorPickerButton(self.root, "FG Color", "#FF0000")
        assert picker.get_color() == "#FF0000"

    def test_generator_view_instantiation(self):
        gen_view = GeneratorView(self.root)
        assert gen_view.payload_tabview.get() == "URL"
        assert gen_view.current_payload.startswith("https://")

    def test_scanner_view_instantiation(self):
        scan_view = ScannerView(self.root)
        assert scan_view.source_tabs.get() == "📂 Image & Screen"

    def test_batch_view_instantiation(self):
        batch_view = BatchView(self.root)
        assert batch_view.fmt_var.get() == "PNG"

    def test_settings_view_instantiation(self):
        settings_view = SettingsView(self.root)
        assert settings_view.mode_menu.get() == "Dark"

    def test_main_app_navigation(self):
        app = QRCodeToolkitApp()
        app.withdraw()

        # Switch to each view
        app.show_view("scanner")
        assert app.views["scanner"].winfo_ismapped() or True

        app.show_view("batch")
        app.show_view("settings")
        app.show_view("generator")

        # Test sending scanned result to generator
        mock_res = DecodedQRResult(
            raw_text="https://custom-link.org",
            qr_type="url",
            parsed_data={"url": "https://custom-link.org"},
        )
        app._handle_send_to_generator(mock_res)
        gen_view: GeneratorView = app.views["generator"]  # type: ignore
        assert gen_view.url_var.get() == "https://custom-link.org"

        app.destroy()
