"""Unit tests for QR code generation and multi-format exports."""

import io
from pathlib import Path
from PIL import Image

from app.generator import QRGenerator
from app.styling import QRStyleConfig


class TestGenerator:
    """Test suite for generation, module drawers, logo compositing, and exports."""

    def test_render_square_modules(self):
        cfg = QRStyleConfig(module_drawer="Square", custom_size=300)
        gen = QRGenerator(cfg)
        img = gen.render_image("https://example.com", target_size=300)
        assert isinstance(img, Image.Image)
        assert img.size == (300, 300)

    def test_render_rounded_modules(self):
        cfg = QRStyleConfig(module_drawer="Rounded", custom_size=300)
        gen = QRGenerator(cfg)
        img = gen.render_image("https://example.com", target_size=300)
        assert isinstance(img, Image.Image)
        assert img.size == (300, 300)

    def test_render_circle_modules(self):
        cfg = QRStyleConfig(module_drawer="Circle", custom_size=300)
        gen = QRGenerator(cfg)
        img = gen.render_image("https://example.com", target_size=300)
        assert isinstance(img, Image.Image)
        assert img.size == (300, 300)

    def test_render_gapped_modules(self):
        cfg = QRStyleConfig(module_drawer="Gapped", custom_size=300)
        gen = QRGenerator(cfg)
        img = gen.render_image("https://example.com", target_size=300)
        assert isinstance(img, Image.Image)
        assert img.size == (300, 300)

    def test_render_with_logo(self, tmp_path: Path):
        # Create a mock logo image
        logo_path = tmp_path / "mock_logo.png"
        logo_img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        logo_img.save(logo_path)

        cfg = QRStyleConfig(
            logo_path=str(logo_path),
            logo_scale=0.20,
            error_correction="H",
        )
        gen = QRGenerator(cfg)
        img = gen.render_image("https://example.com", target_size=400)
        assert isinstance(img, Image.Image)
        assert img.size == (400, 400)

    def test_to_svg(self):
        cfg = QRStyleConfig(fg_color="#00E5FF", bg_color="#0A0E17")
        gen = QRGenerator(cfg)
        svg_str = gen.to_svg("https://example.com", target_size=400)
        assert svg_str.startswith("<svg")
        assert svg_str.endswith("</svg>")
        assert 'fill="#00E5FF"' in svg_str
        assert 'fill="#0A0E17"' in svg_str

    def test_export_file_png(self, tmp_path: Path):
        gen = QRGenerator()
        out_p = tmp_path / "test_qr.png"
        saved = gen.export_file("https://example.com", out_p, file_format="PNG")
        assert saved.exists()
        assert saved.stat().st_size > 0

    def test_export_file_jpg(self, tmp_path: Path):
        gen = QRGenerator()
        out_p = tmp_path / "test_qr.jpg"
        saved = gen.export_file("https://example.com", out_p, file_format="JPG")
        assert saved.exists()
        assert saved.stat().st_size > 0

    def test_export_file_svg(self, tmp_path: Path):
        gen = QRGenerator()
        out_p = tmp_path / "test_qr.svg"
        saved = gen.export_file("https://example.com", out_p, file_format="SVG")
        assert saved.exists()
        content = saved.read_text(encoding="utf-8")
        assert "<svg" in content

    def test_export_file_pdf(self, tmp_path: Path):
        gen = QRGenerator()
        out_p = tmp_path / "test_qr.pdf"
        saved = gen.export_file("https://example.com", out_p, file_format="PDF")
        assert saved.exists()
        assert saved.stat().st_size > 0

    def test_render_with_nonexistent_logo(self):
        cfg = QRStyleConfig(logo_path="non_existent_logo_123.png")
        gen = QRGenerator(cfg)
        img = gen.render_image("https://example.com", target_size=300)
        assert isinstance(img, Image.Image)

    def test_copy_to_clipboard(self):
        gen = QRGenerator()
        res = gen.copy_to_clipboard("https://example.com")
        # On Windows or with tkinter, should return a boolean
        assert isinstance(res, bool)

