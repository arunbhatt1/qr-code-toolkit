"""Interactive Single QR Generator View with Live Preview and Style Studio."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Callable, Optional

import customtkinter as ctk
from PIL import Image, ImageTk

from app.generator import QRGenerator
from app.gui.components import ColorPickerButton, ToastNotification
from app.payloads import (
    build_email_payload,
    build_location_payload,
    build_phone_payload,
    build_sms_payload,
    build_text_payload,
    build_url_payload,
    build_vcard_payload,
    build_wifi_payload,
)
from app.styling import COLOR_PRESETS, SIZE_PRESETS, QRStyleConfig


class GeneratorView(ctk.CTkFrame):
    """Main generator view providing payload configuration and real-time styled preview."""

    def __init__(self, master: ctk.CTkBaseClass, on_toast: Optional[Callable[[str, str], None]] = None) -> None:
        super().__init__(master, fg_color="transparent")
        self.on_toast = on_toast
        self.style_config = QRStyleConfig()
        self.generator = QRGenerator(self.style_config)
        self.current_payload = "https://github.com"
        self._preview_ctk_image: Optional[ctk.CTkImage] = None
        self._debounce_timer: Optional[str] = None

        self._build_ui()
        self._schedule_render(immediate=True)

    def _build_ui(self) -> None:
        """Construct the two-column generator layout."""
        self.grid_columnconfigure(0, weight=1, minsize=420)
        self.grid_columnconfigure(1, weight=1, minsize=420)
        self.grid_rowconfigure(0, weight=1)

        # Left Column: Inputs & Style Studio in a scrollable frame
        self.left_col = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=0)
        self._build_payload_section()
        self._build_style_section()

        # Right Column: Live Preview & Export Toolbar
        self.right_col = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=12)
        self.right_col.grid(row=0, column=1, sticky="nsew", padx=(12, 0), pady=0)
        self._build_preview_section()

    def _build_payload_section(self) -> None:
        """Create payload type tab selector and dynamic input fields."""
        card = ctk.CTkFrame(self.left_col, fg_color="#1E293B", corner_radius=12)
        card.pack(fill="x", pady=(0, 16), padx=2)

        header = ctk.CTkLabel(
            card,
            text="1. Choose Content Type",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        )
        header.pack(fill="x", padx=16, pady=(16, 8))

        # Payload Tabs
        self.payload_tabview = ctk.CTkTabview(
            card,
            height=200,
            command=self._on_payload_tab_changed,
        )
        self.payload_tabview.pack(fill="x", padx=12, pady=(0, 12))

        types = ["URL", "Text", "Wi-Fi", "vCard", "Email", "Phone", "SMS", "Location"]
        for t in types:
            self.payload_tabview.add(t)

        self._build_url_form(self.payload_tabview.tab("URL"))
        self._build_text_form(self.payload_tabview.tab("Text"))
        self._build_wifi_form(self.payload_tabview.tab("Wi-Fi"))
        self._build_vcard_form(self.payload_tabview.tab("vCard"))
        self._build_email_form(self.payload_tabview.tab("Email"))
        self._build_phone_form(self.payload_tabview.tab("Phone"))
        self._build_sms_form(self.payload_tabview.tab("SMS"))
        self._build_location_form(self.payload_tabview.tab("Location"))

    # --- Payload Form Builders ---

    def _build_url_form(self, tab: ctk.CTkFrame) -> None:
        ctk.CTkLabel(tab, text="Website URL:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x", pady=(4, 2))
        self.url_var = tk.StringVar(value="https://github.com")
        self.url_entry = ctk.CTkEntry(tab, textvariable=self.url_var, placeholder_text="e.g., https://example.com")
        self.url_entry.pack(fill="x", pady=(0, 8))
        self.url_var.trace_add("write", lambda *_: self._schedule_render())

    def _build_text_form(self, tab: ctk.CTkFrame) -> None:
        ctk.CTkLabel(tab, text="Plain Text Content:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x", pady=(4, 2))
        self.text_box = ctk.CTkTextbox(tab, height=90)
        self.text_box.insert("1.0", "Hello, World! Created with QR Code Toolkit.")
        self.text_box.pack(fill="x", pady=(0, 8))
        self.text_box.bind("<KeyRelease>", lambda *_: self._schedule_render())

    def _build_wifi_form(self, tab: ctk.CTkFrame) -> None:
        grid = ctk.CTkFrame(tab, fg_color="transparent")
        grid.pack(fill="x")
        grid.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(grid, text="Network Name (SSID):", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").grid(row=0, column=0, sticky="w", padx=4, pady=(2, 2))
        ctk.CTkLabel(grid, text="Security:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").grid(row=0, column=1, sticky="w", padx=4, pady=(2, 2))

        self.wifi_ssid_var = tk.StringVar(value="Home-WiFi")
        self.wifi_ssid_entry = ctk.CTkEntry(grid, textvariable=self.wifi_ssid_var, placeholder_text="SSID")
        self.wifi_ssid_entry.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 6))

        self.wifi_sec_var = tk.StringVar(value="WPA")
        self.wifi_sec_opt = ctk.CTkOptionMenu(
            grid,
            values=["WPA", "WPA2", "WPA3", "WEP", "nopass"],
            variable=self.wifi_sec_var,
            command=lambda _: self._schedule_render(),
        )
        self.wifi_sec_opt.grid(row=1, column=1, sticky="ew", padx=4, pady=(0, 6))

        ctk.CTkLabel(grid, text="Password:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").grid(row=2, column=0, sticky="w", padx=4, pady=(2, 2))
        self.wifi_pass_var = tk.StringVar(value="SecurePass123")
        self.wifi_pass_entry = ctk.CTkEntry(grid, textvariable=self.wifi_pass_var, show="•")
        self.wifi_pass_entry.grid(row=3, column=0, sticky="ew", padx=4, pady=(0, 6))

        self.wifi_hidden_var = tk.BooleanVar(value=False)
        self.wifi_hidden_chk = ctk.CTkCheckBox(grid, text="Hidden Network", variable=self.wifi_hidden_var, command=self._schedule_render)
        self.wifi_hidden_chk.grid(row=3, column=1, sticky="w", padx=8, pady=(0, 6))

        self.wifi_ssid_var.trace_add("write", lambda *_: self._schedule_render())
        self.wifi_pass_var.trace_add("write", lambda *_: self._schedule_render())

    def _build_vcard_form(self, tab: ctk.CTkFrame) -> None:
        grid = ctk.CTkFrame(tab, fg_color="transparent")
        grid.pack(fill="x")
        grid.grid_columnconfigure((0, 1), weight=1)

        self.vcard_name_var = tk.StringVar(value="Jane Doe")
        self.vcard_org_var = tk.StringVar(value="Acme Corp")
        self.vcard_phone_var = tk.StringVar(value="+1 555 123 4567")
        self.vcard_email_var = tk.StringVar(value="jane.doe@example.com")
        self.vcard_web_var = tk.StringVar(value="https://janedoe.me")
        self.vcard_addr_var = tk.StringVar(value="123 Tech Blvd, City")

        fields = [
            ("Full Name:", self.vcard_name_var, 0, 0),
            ("Company / Org:", self.vcard_org_var, 0, 1),
            ("Phone Number:", self.vcard_phone_var, 2, 0),
            ("Email Address:", self.vcard_email_var, 2, 1),
            ("Website:", self.vcard_web_var, 4, 0),
            ("Address:", self.vcard_addr_var, 4, 1),
        ]

        for label_t, var, r, c in fields:
            ctk.CTkLabel(grid, text=label_t, font=ctk.CTkFont(size=11, weight="bold"), anchor="w").grid(row=r, column=c, sticky="w", padx=4, pady=(2, 1))
            entry = ctk.CTkEntry(grid, textvariable=var, height=28)
            entry.grid(row=r + 1, column=c, sticky="ew", padx=4, pady=(0, 4))
            var.trace_add("write", lambda *_: self._schedule_render())

    def _build_email_form(self, tab: ctk.CTkFrame) -> None:
        self.email_to_var = tk.StringVar(value="hello@example.com")
        self.email_sub_var = tk.StringVar(value="Inquiry via QR Code")

        ctk.CTkLabel(tab, text="Recipient Email:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x", pady=(2, 1))
        ctk.CTkEntry(tab, textvariable=self.email_to_var).pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(tab, text="Subject Line:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x", pady=(2, 1))
        ctk.CTkEntry(tab, textvariable=self.email_sub_var).pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(tab, text="Body Message:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x", pady=(2, 1))
        self.email_body_box = ctk.CTkTextbox(tab, height=45)
        self.email_body_box.insert("1.0", "Hello,\nI'd like to get in touch.")
        self.email_body_box.pack(fill="x", pady=(0, 4))
        self.email_body_box.bind("<KeyRelease>", lambda *_: self._schedule_render())

        self.email_to_var.trace_add("write", lambda *_: self._schedule_render())
        self.email_sub_var.trace_add("write", lambda *_: self._schedule_render())

    def _build_phone_form(self, tab: ctk.CTkFrame) -> None:
        ctk.CTkLabel(tab, text="Phone Number:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x", pady=(4, 2))
        self.phone_var = tk.StringVar(value="+1 800 555 0199")
        ctk.CTkEntry(tab, textvariable=self.phone_var, placeholder_text="+1 234 567 8900").pack(fill="x", pady=(0, 8))
        self.phone_var.trace_add("write", lambda *_: self._schedule_render())

    def _build_sms_form(self, tab: ctk.CTkFrame) -> None:
        self.sms_phone_var = tk.StringVar(value="+1 800 555 0199")
        ctk.CTkLabel(tab, text="Recipient Phone:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x", pady=(2, 1))
        ctk.CTkEntry(tab, textvariable=self.sms_phone_var).pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(tab, text="SMS Message:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x", pady=(2, 1))
        self.sms_msg_box = ctk.CTkTextbox(tab, height=50)
        self.sms_msg_box.insert("1.0", "Hi! Responding to your QR code.")
        self.sms_msg_box.pack(fill="x", pady=(0, 4))
        self.sms_msg_box.bind("<KeyRelease>", lambda *_: self._schedule_render())
        self.sms_phone_var.trace_add("write", lambda *_: self._schedule_render())

    def _build_location_form(self, tab: ctk.CTkFrame) -> None:
        grid = ctk.CTkFrame(tab, fg_color="transparent")
        grid.pack(fill="x")
        grid.grid_columnconfigure((0, 1), weight=1)

        self.loc_lat_var = tk.StringVar(value="37.774929")
        self.loc_lon_var = tk.StringVar(value="-122.419416")

        ctk.CTkLabel(grid, text="Latitude (-90 to +90):", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").grid(row=0, column=0, sticky="w", padx=4, pady=(2, 1))
        ctk.CTkLabel(grid, text="Longitude (-180 to +180):", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").grid(row=0, column=1, sticky="w", padx=4, pady=(2, 1))

        ctk.CTkEntry(grid, textvariable=self.loc_lat_var).grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 4))
        ctk.CTkEntry(grid, textvariable=self.loc_lon_var).grid(row=1, column=1, sticky="ew", padx=4, pady=(0, 4))

        self.loc_lat_var.trace_add("write", lambda *_: self._schedule_render())
        self.loc_lon_var.trace_add("write", lambda *_: self._schedule_render())

    # --- Style Studio Section ---

    def _build_style_section(self) -> None:
        """Create style customization accordions & controls."""
        card = ctk.CTkFrame(self.left_col, fg_color="#1E293B", corner_radius=12)
        card.pack(fill="x", pady=(0, 16), padx=2)

        header = ctk.CTkLabel(
            card,
            text="2. Style & Customization Studio",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        )
        header.pack(fill="x", padx=16, pady=(16, 12))

        # Color Palette presets
        preset_frame = ctk.CTkFrame(card, fg_color="transparent")
        preset_frame.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(preset_frame, text="Color Presets:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x", pady=(0, 4))

        preset_names = [p[0] for p in COLOR_PRESETS]
        self.preset_menu = ctk.CTkOptionMenu(
            preset_frame,
            values=preset_names,
            command=self._on_preset_selected,
        )
        self.preset_menu.pack(fill="x")

        # Custom Hex Pickers
        colors_grid = ctk.CTkFrame(card, fg_color="transparent")
        colors_grid.pack(fill="x", padx=16, pady=(0, 12))
        colors_grid.grid_columnconfigure((0, 1), weight=1)

        self.fg_picker = ColorPickerButton(
            colors_grid,
            label_text="Foreground Color:",
            initial_color="#000000",
            on_color_changed=self._on_fg_changed,
        )
        self.fg_picker.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.bg_picker = ColorPickerButton(
            colors_grid,
            label_text="Background Color:",
            initial_color="#FFFFFF",
            on_color_changed=self._on_bg_changed,
        )
        self.bg_picker.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        # Module Drawer & Error Correction
        shapes_grid = ctk.CTkFrame(card, fg_color="transparent")
        shapes_grid.pack(fill="x", padx=16, pady=(0, 12))
        shapes_grid.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(shapes_grid, text="Module Style:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").grid(row=0, column=0, sticky="w", padx=2, pady=(0, 2))
        self.drawer_seg = ctk.CTkSegmentedButton(
            shapes_grid,
            values=["Square", "Rounded", "Circle", "Gapped"],
            command=self._on_drawer_changed,
        )
        self.drawer_seg.set("Square")
        self.drawer_seg.grid(row=1, column=0, sticky="ew", padx=(0, 4))

        ctk.CTkLabel(shapes_grid, text="Error Correction:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").grid(row=0, column=1, sticky="w", padx=2, pady=(0, 2))
        self.ec_seg = ctk.CTkSegmentedButton(
            shapes_grid,
            values=["L (7%)", "M (15%)", "Q (25%)", "H (30%)"],
            command=self._on_ec_changed,
        )
        self.ec_seg.set("M (15%)")
        self.ec_seg.grid(row=1, column=1, sticky="ew", padx=(4, 0))

        # Logo Embedding
        logo_frame = ctk.CTkFrame(card, fg_color="transparent")
        logo_frame.pack(fill="x", padx=16, pady=(0, 16))

        ctk.CTkLabel(logo_frame, text="Center Logo / Icon:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x", pady=(0, 4))
        logo_ctrls = ctk.CTkFrame(logo_frame, fg_color="transparent")
        logo_ctrls.pack(fill="x")

        self.logo_path_label = ctk.CTkLabel(logo_ctrls, text="No logo chosen", text_color="#94A3B8", anchor="w")
        self.logo_path_label.pack(side="left", fill="x", expand=True)

        self.btn_browse_logo = ctk.CTkButton(logo_ctrls, text="Choose Logo...", width=110, command=self._browse_logo)
        self.btn_browse_logo.pack(side="right", padx=(4, 0))

        self.btn_clear_logo = ctk.CTkButton(logo_ctrls, text="✕", width=32, fg_color="#334155", hover_color="#475569", command=self._clear_logo)
        self.btn_clear_logo.pack(side="right", padx=(4, 0))

        # Logo Scale Slider
        self.scale_slider_frame = ctk.CTkFrame(logo_frame, fg_color="transparent")
        self.scale_slider_frame.pack(fill="x", pady=(6, 0))

        self.logo_scale_lbl = ctk.CTkLabel(self.scale_slider_frame, text="Logo Size: 20%", font=ctk.CTkFont(size=11))
        self.logo_scale_lbl.pack(side="left")

        self.logo_scale_slider = ctk.CTkSlider(
            self.scale_slider_frame,
            from_=0.10,
            to=0.30,
            number_of_steps=20,
            command=self._on_logo_scale_changed,
        )
        self.logo_scale_slider.set(0.20)
        self.logo_scale_slider.pack(side="right", fill="x", expand=True, padx=(10, 0))

        # Safety warning badge
        self.logo_safety_lbl = ctk.CTkLabel(
            logo_frame,
            text="",
            text_color="#FBBF24",
            font=ctk.CTkFont(size=11),
            anchor="w",
        )
        self.logo_safety_lbl.pack(fill="x", pady=(2, 0))

    # --- Live Preview Section ---

    def _build_preview_section(self) -> None:
        """Build the right column live preview canvas and export toolbar."""
        header_frame = ctk.CTkFrame(self.right_col, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(20, 10))

        title = ctk.CTkLabel(
            header_frame,
            text="Live Preview",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.pack(side="left")

        self.res_badge = ctk.CTkLabel(
            header_frame,
            text="400 × 400 px",
            fg_color="#334155",
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            padx=8,
            pady=2,
        )
        self.res_badge.pack(side="right")

        # Preview Image Box
        self.preview_canvas_frame = ctk.CTkFrame(
            self.right_col,
            fg_color="#0F172A",
            corner_radius=12,
            border_width=1,
            border_color="#334155",
        )
        self.preview_canvas_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.preview_img_label = ctk.CTkLabel(
            self.preview_canvas_frame,
            text="Generating preview...",
        )
        self.preview_img_label.pack(expand=True, padx=20, pady=20)

        # Error banner if payload is invalid
        self.error_banner = ctk.CTkLabel(
            self.right_col,
            text="",
            text_color="#F87171",
            font=ctk.CTkFont(size=12, weight="bold"),
            wraplength=380,
        )
        self.error_banner.pack(fill="x", padx=20, pady=(0, 8))

        # Action Buttons Toolbar
        btn_grid = ctk.CTkFrame(self.right_col, fg_color="transparent")
        btn_grid.pack(fill="x", padx=20, pady=(0, 20))
        btn_grid.grid_columnconfigure((0, 1, 2), weight=1)

        # Row 1: Copy Image, Copy Payload, Save PNG
        self.btn_copy_img = ctk.CTkButton(
            btn_grid,
            text="📋 Copy Image",
            fg_color="#6366F1",
            hover_color="#4F46E5",
            command=self._copy_image_clipboard,
        )
        self.btn_copy_img.grid(row=0, column=0, sticky="ew", padx=3, pady=3)

        self.btn_copy_txt = ctk.CTkButton(
            btn_grid,
            text="📄 Copy Text",
            fg_color="#334155",
            hover_color="#475569",
            command=self._copy_payload_clipboard,
        )
        self.btn_copy_txt.grid(row=0, column=1, sticky="ew", padx=3, pady=3)

        self.btn_save_png = ctk.CTkButton(
            btn_grid,
            text="💾 Save PNG",
            fg_color="#059669",
            hover_color="#047857",
            command=lambda: self._export_as("PNG"),
        )
        self.btn_save_png.grid(row=0, column=2, sticky="ew", padx=3, pady=3)

        # Row 2: Save JPG, Save SVG, Save PDF
        self.btn_save_jpg = ctk.CTkButton(
            btn_grid,
            text="Save JPG",
            fg_color="#334155",
            hover_color="#475569",
            command=lambda: self._export_as("JPG"),
        )
        self.btn_save_jpg.grid(row=1, column=0, sticky="ew", padx=3, pady=3)

        self.btn_save_svg = ctk.CTkButton(
            btn_grid,
            text="Save SVG",
            fg_color="#334155",
            hover_color="#475569",
            command=lambda: self._export_as("SVG"),
        )
        self.btn_save_svg.grid(row=1, column=1, sticky="ew", padx=3, pady=3)

        self.btn_save_pdf = ctk.CTkButton(
            btn_grid,
            text="Save PDF",
            fg_color="#334155",
            hover_color="#475569",
            command=lambda: self._export_as("PDF"),
        )
        self.btn_save_pdf.grid(row=1, column=2, sticky="ew", padx=3, pady=3)

    # --- Event Handlers & Rendering ---

    def _on_payload_tab_changed(self) -> None:
        self._schedule_render(immediate=True)

    def _on_preset_selected(self, preset_name: str) -> None:
        for name, fg, bg in COLOR_PRESETS:
            if name == preset_name:
                self.fg_picker.set_color(fg)
                self.bg_picker.set_color(bg)
                self.style_config.fg_color = fg
                self.style_config.bg_color = bg
                self._schedule_render(immediate=True)
                break

    def _on_fg_changed(self, color_hex: str) -> None:
        self.style_config.fg_color = color_hex
        self._schedule_render()

    def _on_bg_changed(self, color_hex: str) -> None:
        self.style_config.bg_color = color_hex
        self._schedule_render()

    def _on_drawer_changed(self, value: str) -> None:
        self.style_config.module_drawer = value
        self._schedule_render(immediate=True)

    def _on_ec_changed(self, value: str) -> None:
        ec_char = value.split()[0]
        self.style_config.error_correction = ec_char
        self._schedule_render(immediate=True)

    def _on_logo_scale_changed(self, value: float) -> None:
        self.style_config.logo_scale = round(value, 2)
        pct = int(value * 100)
        self.logo_scale_lbl.configure(text=f"Logo Size: {pct}%")
        is_safe, msg = self.style_config.check_logo_safety()
        self.logo_safety_lbl.configure(text=msg if not is_safe else "")
        self._schedule_render()

    def _browse_logo(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select Logo Image",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.ico"), ("All Files", "*.*")],
        )
        if file_path:
            self.style_config.logo_path = file_path
            self.logo_path_label.configure(text=Path(file_path).name, text_color="#38BDF8")
            # If error correction is L or M, auto-bump to H for logo safety
            if self.style_config.error_correction in ("L", "M"):
                self.style_config.error_correction = "H"
                self.ec_seg.set("H (30%)")
            self._schedule_render(immediate=True)

    def _clear_logo(self) -> None:
        self.style_config.logo_path = ""
        self.logo_path_label.configure(text="No logo chosen", text_color="#94A3B8")
        self.logo_safety_lbl.configure(text="")
        self._schedule_render(immediate=True)

    def _extract_active_payload(self) -> str:
        """Extract and build RFC payload based on active tab."""
        active_tab = self.payload_tabview.get()
        if active_tab == "URL":
            return build_url_payload(self.url_var.get())
        elif active_tab == "Text":
            return build_text_payload(self.text_box.get("1.0", "end-1c"))
        elif active_tab == "Wi-Fi":
            return build_wifi_payload(
                ssid=self.wifi_ssid_var.get(),
                password=self.wifi_pass_var.get(),
                security=self.wifi_sec_var.get(),
                hidden=self.wifi_hidden_var.get(),
            )
        elif active_tab == "vCard":
            return build_vcard_payload(
                full_name=self.vcard_name_var.get(),
                org=self.vcard_org_var.get(),
                phone=self.vcard_phone_var.get(),
                email=self.vcard_email_var.get(),
                website=self.vcard_web_var.get(),
                address=self.vcard_addr_var.get(),
            )
        elif active_tab == "Email":
            return build_email_payload(
                email=self.email_to_var.get(),
                subject=self.email_sub_var.get(),
                body=self.email_body_box.get("1.0", "end-1c"),
            )
        elif active_tab == "Phone":
            return build_phone_payload(self.phone_var.get())
        elif active_tab == "SMS":
            return build_sms_payload(
                phone=self.sms_phone_var.get(),
                message=self.sms_msg_box.get("1.0", "end-1c"),
            )
        elif active_tab == "Location":
            return build_location_payload(
                latitude=self.loc_lat_var.get(),
                longitude=self.loc_lon_var.get(),
            )
        return "https://github.com"

    def _schedule_render(self, immediate: bool = False) -> None:
        """Debounce render updates for smooth responsive typing."""
        if self._debounce_timer is not None:
            self.after_cancel(self._debounce_timer)
            self._debounce_timer = None

        if immediate:
            self._render_preview()
        else:
            self._debounce_timer = self.after(120, self._render_preview)

    def _render_preview(self) -> None:
        """Render the QR code image and update the preview widget."""
        try:
            payload = self._extract_active_payload()
            self.current_payload = payload
            self.error_banner.configure(text="")
        except ValueError as err:
            self.error_banner.configure(text=f"⚠️ {str(err)}")
            return

        try:
            # Generate high-res image
            pil_img = self.generator.render_image(
                payload=self.current_payload,
                style=self.style_config,
                target_size=400,
            )

            # Fit nicely in preview box (max 320x320 displayed)
            disp_size = (300, 300)
            self._preview_ctk_image = ctk.CTkImage(
                light_image=pil_img,
                dark_image=pil_img,
                size=disp_size,
            )
            self.preview_img_label.configure(image=self._preview_ctk_image, text="")
        except Exception as exc:
            self.error_banner.configure(text=f"Rendering error: {str(exc)}")

    def _copy_image_clipboard(self) -> None:
        try:
            ok = self.generator.copy_to_clipboard(
                payload=self.current_payload,
                style=self.style_config,
                target_size=600,
            )
            if ok and self.on_toast:
                self.on_toast("QR Code copied to clipboard!", "success")
        except Exception as exc:
            if self.on_toast:
                self.on_toast(f"Failed to copy image: {str(exc)}", "error")

    def _copy_payload_clipboard(self) -> None:
        try:
            self.clipboard_clear()
            self.clipboard_append(self.current_payload)
            self.update()
            if self.on_toast:
                self.on_toast("Payload text copied to clipboard!", "info")
        except Exception as exc:
            if self.on_toast:
                self.on_toast(f"Failed to copy text: {str(exc)}", "error")

    def _export_as(self, fmt: str) -> None:
        ext = fmt.lower()
        if fmt == "JPG":
            ext = "jpg"

        file_types = {
            "PNG": [("PNG Image", "*.png")],
            "JPG": [("JPEG Image", "*.jpg;*.jpeg")],
            "SVG": [("Scalable Vector Graphics", "*.svg")],
            "PDF": [("Portable Document Format", "*.pdf")],
        }

        active_tab = self.payload_tabview.get().lower()
        default_name = f"qr_{active_tab}.{ext}"

        dest_path = filedialog.asksaveasfilename(
            title=f"Save QR Code as {fmt}",
            defaultextension=f".{ext}",
            initialfile=default_name,
            filetypes=file_types.get(fmt, [("All Files", "*.*")]),
        )

        if not dest_path:
            return

        try:
            self.generator.export_file(
                payload=self.current_payload,
                output_path=dest_path,
                file_format=fmt,
                style=self.style_config,
                target_size=800 if fmt in ("PNG", "JPG", "PDF") else 400,
            )
            if self.on_toast:
                self.on_toast(f"Saved successfully: {Path(dest_path).name}", "success")
        except Exception as exc:
            if self.on_toast:
                self.on_toast(f"Export failed: {str(exc)}", "error")
