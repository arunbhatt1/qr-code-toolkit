"""Unit tests for styling configurations and color conversion."""

import qrcode.constants

from app.styling import (
    COLOR_PRESETS,
    SIZE_PRESETS,
    QRStyleConfig,
    hex_to_rgb,
    normalize_hex_color,
)


class TestStyling:
    """Test suite for style parameters, hex parser, and logo safety calculations."""

    def test_normalize_hex_color_3digit(self):
        assert normalize_hex_color("#FFF") == "#FFFFFF"
        assert normalize_hex_color("000") == "#000000"

    def test_normalize_hex_color_6digit(self):
        assert normalize_hex_color("#6366f1") == "#6366F1"
        assert normalize_hex_color("10B981") == "#10B981"

    def test_normalize_hex_color_invalid(self):
        assert normalize_hex_color("not_a_color", default="#000000") == "#000000"

    def test_hex_to_rgb(self):
        assert hex_to_rgb("#FFFFFF") == (255, 255, 255)
        assert hex_to_rgb("#000000") == (0, 0, 0)
        assert hex_to_rgb("#FF0000") == (255, 0, 0)

    def test_style_config_target_size(self):
        cfg = QRStyleConfig(size_preset="Small")
        assert cfg.target_size == SIZE_PRESETS["Small"]

        cfg2 = QRStyleConfig(size_preset="Custom", custom_size=550)
        assert cfg2.target_size == 550

    def test_style_config_ec_constant(self):
        cfg = QRStyleConfig(error_correction="H")
        assert cfg.ec_constant == qrcode.constants.ERROR_CORRECT_H

    def test_style_config_logo_safety(self):
        cfg = QRStyleConfig(logo_path="some_logo.png", logo_scale=0.20)
        is_safe, msg = cfg.check_logo_safety()
        assert is_safe is True

        cfg_unsafe = QRStyleConfig(logo_path="some_logo.png", logo_scale=0.28)
        is_safe_2, msg_2 = cfg_unsafe.check_logo_safety()
        assert is_safe_2 is False
        assert "Warning" in msg_2
