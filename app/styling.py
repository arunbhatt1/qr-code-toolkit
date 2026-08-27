"""Styling parameters, color management, and drawer configurations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Tuple

import qrcode.constants

# Map error correction strings to qrcode constants
ERROR_CORRECTION_MAP = {
    "L": qrcode.constants.ERROR_CORRECT_L,
    "M": qrcode.constants.ERROR_CORRECT_M,
    "Q": qrcode.constants.ERROR_CORRECT_Q,
    "H": qrcode.constants.ERROR_CORRECT_H,
}

ERROR_CORRECTION_NAMES = {
    qrcode.constants.ERROR_CORRECT_L: "Low (7%)",
    qrcode.constants.ERROR_CORRECT_M: "Medium (15%)",
    qrcode.constants.ERROR_CORRECT_Q: "Quartile (25%)",
    qrcode.constants.ERROR_CORRECT_H: "High (30%)",
}

SIZE_PRESETS = {
    "Small": 250,
    "Medium": 400,
    "Large": 600,
}

COLOR_PRESETS = [
    ("Classic Dark", "#000000", "#FFFFFF"),
    ("Cyber Cyan", "#00E5FF", "#0A0E17"),
    ("Electric Indigo", "#6366F1", "#0F172A"),
    ("Emerald Green", "#10B981", "#064E3B"),
    ("Sunset Crimson", "#EF4444", "#FFFFFF"),
    ("Royal Violet", "#8B5CF6", "#1E1B4B"),
    ("Amber Gold", "#F59E0B", "#1C1917"),
    ("Slate Modern", "#334155", "#F8FAFC"),
]

HEX_COLOR_REGEX = re.compile(r"^#?([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$")


def normalize_hex_color(hex_str: str, default: str = "#000000") -> str:
    """Normalize and validate a hex color string to #RRGGBB."""
    cleaned = hex_str.strip()
    if not cleaned.startswith("#"):
        cleaned = f"#{cleaned}"

    match = HEX_COLOR_REGEX.match(cleaned)
    if not match:
        return default

    hex_val = match.group(1)
    if len(hex_val) == 3:
        # Expand #RGB to #RRGGBB
        return f"#{hex_val[0]*2}{hex_val[1]*2}{hex_val[2]*2}".upper()
    return f"#{hex_val}".upper()


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    normalized = normalize_hex_color(hex_str).lstrip("#")
    return int(normalized[0:2], 16), int(normalized[2:4], 16), int(normalized[4:6], 16)


@dataclass
class QRStyleConfig:
    """Configuration options for rendering a QR code."""

    size_preset: str = "Medium"
    custom_size: int = 400
    border: int = 4
    error_correction: str = "M"
    fg_color: str = "#000000"
    bg_color: str = "#FFFFFF"
    module_drawer: str = "Square"  # "Square" or "Rounded"
    logo_path: str = ""
    logo_scale: float = 0.20  # Proportion of QR code width for logo (0.10 to 0.30)

    @property
    def target_size(self) -> int:
        if self.size_preset in SIZE_PRESETS:
            return SIZE_PRESETS[self.size_preset]
        return max(100, min(2000, self.custom_size))

    @property
    def ec_constant(self) -> int:
        # If a logo is present, enforce at least 'Q' or 'H'
        ec = self.error_correction.upper()
        if self.logo_path and ec in ("L", "M"):
            ec = "H"
        return ERROR_CORRECTION_MAP.get(ec, qrcode.constants.ERROR_CORRECT_M)

    @property
    def normalized_fg(self) -> str:
        return normalize_hex_color(self.fg_color, "#000000")

    @property
    def normalized_bg(self) -> str:
        return normalize_hex_color(self.bg_color, "#FFFFFF")

    def check_logo_safety(self) -> Tuple[bool, str]:
        """Check if logo scale is safe for reliable scanning."""
        if not self.logo_path:
            return True, ""
        if self.logo_scale > 0.25:
            return (
                False,
                "Warning: Logo covers >25% of QR code. This may reduce scan reliability on some devices.",
            )
        return True, ""
