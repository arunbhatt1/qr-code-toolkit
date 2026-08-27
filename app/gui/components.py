"""Reusable UI components and widgets for QR Code Toolkit GUI."""

from __future__ import annotations

import tkinter as tk
from tkinter import colorchooser
from typing import Callable, List, Optional, Tuple

import customtkinter as ctk
from PIL import Image

from app.styling import normalize_hex_color


class ToastNotification(ctk.CTkFrame):
    """Floating toast notification for user feedback."""

    def __init__(
        self,
        master: ctk.CTk,
        message: str,
        toast_type: str = "info",  # "info", "success", "warning", "error"
        duration_ms: int = 3000,
    ) -> None:
        colors = {
            "info": ("#1E293B", "#38BDF8"),
            "success": ("#064E3B", "#34D399"),
            "warning": ("#78350F", "#FBBF24"),
            "error": ("#7F1D1D", "#F87171"),
        }
        bg_col, fg_col = colors.get(toast_type, colors["info"])

        super().__init__(
            master,
            fg_color=bg_col,
            corner_radius=8,
            border_width=1,
            border_color=fg_col,
        )

        icons = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}
        icon_text = icons.get(toast_type, "ℹ️")

        self.label = ctk.CTkLabel(
            self,
            text=f"{icon_text}  {message}",
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.label.pack(side="left", padx=16, pady=10)

        self.close_btn = ctk.CTkButton(
            self,
            text="✕",
            width=24,
            height=24,
            fg_color="transparent",
            hover_color="#334155",
            text_color="#CBD5E1",
            command=self.dismiss,
        )
        self.close_btn.pack(side="right", padx=(0, 10), pady=10)

        # Place toast at bottom center of master window
        self.place(relx=0.5, rely=0.92, anchor="center")
        self.after(duration_ms, self.dismiss)

    def dismiss(self) -> None:
        """Fade out or destroy toast."""
        try:
            self.destroy()
        except Exception:
            pass


class ColorPickerButton(ctk.CTkFrame):
    """Interactive color swatch with hex entry and native color picker."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        label_text: str,
        initial_color: str = "#000000",
        on_color_changed: Optional[Callable[[str], None]] = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.on_color_changed = on_color_changed
        self.current_color = normalize_hex_color(initial_color)

        self.label = ctk.CTkLabel(
            self,
            text=label_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )
        self.label.pack(fill="x", pady=(0, 4))

        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        controls_frame.pack(fill="x")

        # Swatch button
        self.swatch = ctk.CTkButton(
            controls_frame,
            text="",
            width=32,
            height=32,
            corner_radius=6,
            fg_color=self.current_color,
            hover_color=self.current_color,
            border_width=1,
            border_color="#475569",
            command=self._open_picker,
        )
        self.swatch.pack(side="left", padx=(0, 8))

        # Hex Entry
        self.hex_var = tk.StringVar(value=self.current_color)
        self.hex_entry = ctk.CTkEntry(
            controls_frame,
            textvariable=self.hex_var,
            width=100,
            height=32,
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        self.hex_entry.pack(side="left", fill="x", expand=True)
        self.hex_entry.bind("<FocusOut>", self._on_entry_changed)
        self.hex_entry.bind("<Return>", self._on_entry_changed)

    def _open_picker(self) -> None:
        """Launch system color dialog."""
        _, hex_code = colorchooser.askcolor(
            color=self.current_color,
            title="Select QR Color",
        )
        if hex_code:
            self.set_color(hex_code)

    def _on_entry_changed(self, event=None) -> None:
        """Handle manual hex string edits."""
        val = self.hex_var.get().strip()
        norm = normalize_hex_color(val, self.current_color)
        self.set_color(norm)

    def set_color(self, hex_code: str) -> None:
        """Update color state and trigger callback."""
        self.current_color = normalize_hex_color(hex_code)
        self.hex_var.set(self.current_color)
        self.swatch.configure(fg_color=self.current_color, hover_color=self.current_color)
        if self.on_color_changed:
            self.on_color_changed(self.current_color)

    def get_color(self) -> str:
        return self.current_color


class StatusBadge(ctk.CTkLabel):
    """Color-coded status badge."""

    def __init__(self, master: ctk.CTkBaseClass, status: str) -> None:
        palette = {
            "success": ("#064E3B", "#34D399", "SUCCESS"),
            "pending": ("#1E293B", "#94A3B8", "PENDING"),
            "failed": ("#7F1D1D", "#F87171", "FAILED"),
            "skipped": ("#78350F", "#FBBF24", "SKIPPED"),
        }
        bg, fg, label = palette.get(status.lower(), ("#1E293B", "#94A3B8", status.upper()))

        super().__init__(
            master,
            text=f" {label} ",
            fg_color=bg,
            text_color=fg,
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
        )
