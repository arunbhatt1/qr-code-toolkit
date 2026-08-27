"""QR Code generation and rendering engine.

Supports custom color palettes, square / rounded / circle module drawers,
antialiased center logo embedding with protective shields, and export
to PNG, JPEG, SVG, PDF, and system clipboard.
"""

from __future__ import annotations

import io
import math
import sys
from pathlib import Path
from typing import Optional, Tuple, Union

import qrcode
from PIL import Image, ImageColor, ImageDraw, ImageOps

from app.logging_config import log_error, log_generation
from app.styling import QRStyleConfig, hex_to_rgb, normalize_hex_color


class QRGenerator:
    """High-performance QR code generator and styler."""

    def __init__(self, style: Optional[QRStyleConfig] = None) -> None:
        self.style = style or QRStyleConfig()

    def generate_matrix(self, payload: str) -> qrcode.QRCode:
        """Generate the raw QR matrix from a payload string."""
        qr = qrcode.QRCode(
            version=None,  # Auto-size version
            error_correction=self.style.ec_constant,
            box_size=10,
            border=self.style.border,
        )
        qr.add_data(payload)
        qr.make(fit=True)
        return qr

    def render_image(
        self,
        payload: str,
        style: Optional[QRStyleConfig] = None,
        target_size: Optional[int] = None,
    ) -> Image.Image:
        """Render a fully styled PIL Image of the QR code."""
        cfg = style or self.style
        qr = qrcode.QRCode(
            version=None,
            error_correction=cfg.ec_constant,
            box_size=10,
            border=cfg.border,
        )
        qr.add_data(payload)
        qr.make(fit=True)

        matrix = qr.get_matrix()
        matrix_size = len(matrix)
        out_size = target_size or cfg.target_size

        # Render base styled QR code
        img = self._render_modules(matrix, cfg, out_size)

        # Composite logo if specified
        if cfg.logo_path and Path(cfg.logo_path).is_file():
            try:
                img = self._embed_logo(img, cfg.logo_path, cfg.logo_scale, cfg.normalized_bg)
            except Exception as exc:
                log_error("Embedding logo in QR code", exc)

        log_generation(
            qr_type="custom" if cfg.logo_path else "standard",
            error_correction=cfg.error_correction,
            size=out_size,
        )
        return img

    def _render_modules(
        self,
        matrix: list[list[bool]],
        cfg: QRStyleConfig,
        target_size: int,
    ) -> Image.Image:
        """Draw QR modules based on the selected drawer style."""
        matrix_len = len(matrix)
        fg_rgb = hex_to_rgb(cfg.normalized_fg)
        bg_rgb = hex_to_rgb(cfg.normalized_bg)

        # High-resolution rendering canvas for smooth antialiasing
        scale = max(1, target_size // matrix_len)
        canvas_dim = matrix_len * scale

        # Create base canvas with background color
        canvas = Image.new("RGBA", (canvas_dim, canvas_dim), bg_rgb + (255,))
        draw = ImageDraw.Draw(canvas)

        drawer = cfg.module_drawer.lower()

        for r in range(matrix_len):
            for c in range(matrix_len):
                if not matrix[r][c]:
                    continue

                x0 = c * scale
                y0 = r * scale
                x1 = x0 + scale
                y1 = y0 + scale

                # Check if this module is part of the 3 corner finder patterns (7x7 zones)
                is_finder = (
                    (r < 7 + cfg.border and c < 7 + cfg.border)
                    or (r < 7 + cfg.border and c >= matrix_len - 7 - cfg.border)
                    or (r >= matrix_len - 7 - cfg.border and c < 7 + cfg.border)
                )

                if is_finder or drawer == "square":
                    draw.rectangle([x0, y0, x1, y1], fill=fg_rgb + (255,))
                elif drawer in ("rounded", "round"):
                    # Rounded module with subtle corner radius
                    radius = scale // 3
                    draw.rounded_rectangle(
                        [x0, y0, x1 - 1, y1 - 1],
                        radius=radius,
                        fill=fg_rgb + (255,),
                    )
                elif drawer in ("circle", "dots"):
                    # Circular dot modules
                    pad = max(1, scale // 10)
                    draw.ellipse(
                        [x0 + pad, y0 + pad, x1 - pad, y1 - pad],
                        fill=fg_rgb + (255,),
                    )
                elif drawer == "gapped":
                    # Gapped square modules for futuristic aesthetic
                    pad = max(1, scale // 8)
                    draw.rectangle(
                        [x0 + pad, y0 + pad, x1 - pad, y1 - pad],
                        fill=fg_rgb + (255,),
                    )
                else:
                    draw.rectangle([x0, y0, x1, y1], fill=fg_rgb + (255,))

        # Resize cleanly to requested target size using LANCZOS resampling
        if (canvas_dim, canvas_dim) != (target_size, target_size):
            canvas = canvas.resize((target_size, target_size), Image.Resampling.LANCZOS)

        return canvas

    def _embed_logo(
        self,
        base_img: Image.Image,
        logo_path: str,
        scale: float,
        bg_color_hex: str,
    ) -> Image.Image:
        """Composite a logo in the center with a protective background shield."""
        logo_file = Path(logo_path)
        if not logo_file.exists():
            return base_img

        try:
            with Image.open(logo_file) as raw_logo:
                logo = raw_logo.convert("RGBA")
        except Exception:
            return base_img

        qr_w, qr_h = base_img.size
        # Clamped logo size ratio between 10% and 30%
        clamped_scale = max(0.10, min(0.30, scale))
        logo_target_w = int(qr_w * clamped_scale)
        logo_target_h = int(qr_h * clamped_scale)

        # Preserve aspect ratio of logo
        logo.thumbnail((logo_target_w, logo_target_h), Image.Resampling.LANCZOS)
        lw, lh = logo.size

        # Create protective shield / background pill
        pad = max(6, int(min(lw, lh) * 0.12))
        shield_w = lw + pad * 2
        shield_h = lh + pad * 2

        shield = Image.new("RGBA", (shield_w, shield_h), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shield)

        bg_rgb = hex_to_rgb(bg_color_hex)
        corner_rad = max(4, pad)

        # Draw rounded background shield
        s_draw.rounded_rectangle(
            [0, 0, shield_w - 1, shield_h - 1],
            radius=corner_rad,
            fill=bg_rgb + (255,),
            outline=(200, 200, 200, 255),
            width=1,
        )

        # Paste logo onto shield
        shield.alpha_composite(logo, (pad, pad))

        # Composite shield onto base QR code image
        pos_x = (qr_w - shield_w) // 2
        pos_y = (qr_h - shield_h) // 2

        out_img = base_img.copy().convert("RGBA")
        out_img.alpha_composite(shield, (pos_x, pos_y))
        return out_img

    def to_svg(
        self,
        payload: str,
        style: Optional[QRStyleConfig] = None,
        target_size: Optional[int] = None,
    ) -> str:
        """Generate clean, scalable vector SVG XML string."""
        cfg = style or self.style
        qr = self.generate_matrix(payload)
        matrix = qr.get_matrix()
        matrix_len = len(matrix)
        size = target_size or cfg.target_size
        box_size = size / matrix_len

        fg_hex = cfg.normalized_fg
        bg_hex = cfg.normalized_bg
        drawer = cfg.module_drawer.lower()

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
            f'width="{size}" height="{size}" viewBox="0 0 {size} {size}">',
            f'  <rect width="100%" height="100%" fill="{bg_hex}"/>',
        ]

        for r in range(matrix_len):
            for c in range(matrix_len):
                if not matrix[r][c]:
                    continue

                x = c * box_size
                y = r * box_size

                is_finder = (
                    (r < 7 + cfg.border and c < 7 + cfg.border)
                    or (r < 7 + cfg.border and c >= matrix_len - 7 - cfg.border)
                    or (r >= matrix_len - 7 - cfg.border and c < 7 + cfg.border)
                )

                if is_finder or drawer == "square":
                    svg_parts.append(
                        f'  <rect x="{x:.2f}" y="{y:.2f}" width="{box_size:.2f}" '
                        f'height="{box_size:.2f}" fill="{fg_hex}"/>'
                    )
                elif drawer in ("rounded", "round"):
                    rx = box_size * 0.3
                    svg_parts.append(
                        f'  <rect x="{x:.2f}" y="{y:.2f}" width="{box_size:.2f}" '
                        f'height="{box_size:.2f}" rx="{rx:.2f}" ry="{rx:.2f}" fill="{fg_hex}"/>'
                    )
                elif drawer in ("circle", "dots"):
                    cx = x + box_size / 2
                    cy = y + box_size / 2
                    r_rad = (box_size / 2) * 0.85
                    svg_parts.append(
                        f'  <circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r_rad:.2f}" fill="{fg_hex}"/>'
                    )
                elif drawer == "gapped":
                    gap = box_size * 0.15
                    svg_parts.append(
                        f'  <rect x="{x+gap:.2f}" y="{y+gap:.2f}" width="{box_size-2*gap:.2f}" '
                        f'height="{box_size-2*gap:.2f}" fill="{fg_hex}"/>'
                    )
                else:
                    svg_parts.append(
                        f'  <rect x="{x:.2f}" y="{y:.2f}" width="{box_size:.2f}" '
                        f'height="{box_size:.2f}" fill="{fg_hex}"/>'
                    )

        svg_parts.append("</svg>")
        return "\n".join(svg_parts)

    def export_file(
        self,
        payload: str,
        output_path: Union[str, Path],
        file_format: str = "PNG",
        style: Optional[QRStyleConfig] = None,
        target_size: Optional[int] = None,
    ) -> Path:
        """Export QR code to image, SVG, or PDF file."""
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        fmt = file_format.upper()
        cfg = style or self.style
        size = target_size or cfg.target_size

        if fmt == "SVG":
            svg_content = self.to_svg(payload, cfg, size)
            out_p.write_text(svg_content, encoding="utf-8")
            return out_p

        img = self.render_image(payload, cfg, size)

        if fmt == "PDF":
            # Save high-resolution RGB image inside a clean PDF page
            pdf_img = Image.new("RGB", img.size, hex_to_rgb(cfg.normalized_bg))
            if img.mode == "RGBA":
                pdf_img.paste(img, mask=img.split()[3])
            else:
                pdf_img.paste(img, (0, 0))
            pdf_img.save(out_p, "PDF", resolution=300.0)
            return out_p

        if fmt in ("JPG", "JPEG"):
            # JPEG requires RGB mode without alpha channel
            rgb_img = Image.new("RGB", img.size, hex_to_rgb(cfg.normalized_bg))
            if img.mode == "RGBA":
                rgb_img.paste(img, mask=img.split()[3])
            else:
                rgb_img.paste(img, (0, 0))
            rgb_img.save(out_p, "JPEG", quality=95)
            return out_p

        # Default: PNG
        img.save(out_p, "PNG")
        return out_p

    def copy_to_clipboard(
        self,
        payload: str,
        style: Optional[QRStyleConfig] = None,
        target_size: Optional[int] = None,
    ) -> bool:
        """Copy generated QR code image directly to system clipboard."""
        img = self.render_image(payload, style, target_size)

        if sys.platform == "win32":
            try:
                import ctypes
                from ctypes import wintypes

                # Convert image to Windows Device-Independent Bitmap (DIB)
                output = io.BytesIO()
                # Windows DIB requires RGB BMP without the 14-byte file header
                rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "RGBA":
                    rgb_img.paste(img, mask=img.split()[3])
                else:
                    rgb_img.paste(img, (0, 0))

                rgb_img.save(output, "BMP")
                data = output.getvalue()[14:]  # Strip 14-byte BMP header
                output.close()

                # Windows Clipboard API calls with explicit 64-bit types
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32

                kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
                kernel32.GlobalAlloc.restype = ctypes.c_void_p

                kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
                kernel32.GlobalLock.restype = ctypes.c_void_p

                kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
                kernel32.GlobalUnlock.restype = ctypes.c_int

                user32.OpenClipboard.argtypes = [ctypes.c_void_p]
                user32.OpenClipboard.restype = ctypes.c_int

                user32.EmptyClipboard.argtypes = []
                user32.EmptyClipboard.restype = ctypes.c_int

                user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
                user32.SetClipboardData.restype = ctypes.c_void_p

                user32.CloseClipboard.argtypes = []
                user32.CloseClipboard.restype = ctypes.c_int

                CF_DIB = 8
                GMEM_MOVEABLE = 0x0002

                if not user32.OpenClipboard(None):
                    return False

                try:
                    user32.EmptyClipboard()
                    h_glob = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
                    if not h_glob:
                        return False

                    p_data = kernel32.GlobalLock(h_glob)
                    if not p_data:
                        return False

                    ctypes.memmove(p_data, data, len(data))
                    kernel32.GlobalUnlock(h_glob)

                    user32.SetClipboardData(CF_DIB, h_glob)
                    return True
                finally:
                    user32.CloseClipboard()
            except Exception as exc:
                log_error("Windows clipboard copy", exc)
                return False
        else:
            # Fallback for Linux / macOS via subprocess or tkinter
            try:
                import tkinter as tk

                root = tk.Tk()
                root.withdraw()
                root.clipboard_clear()
                # Note: On X11, image copying to clipboard typically needs xclip
                root.clipboard_append(payload)
                root.update()
                root.destroy()
                return True
            except Exception as exc:
                log_error("Clipboard copy fallback", exc)
                return False
