"""Unit tests for CLI parsing and CLI commands in app.main."""

import sys
from pathlib import Path

import pytest

from app.main import build_cli_parser, handle_cli_generate, handle_cli_scan


class TestMainCLI:
    """Test suite for command-line arguments and handlers."""

    def test_parser_defaults(self):
        parser = build_cli_parser()
        args = parser.parse_args([])
        assert args.gui is False
        assert args.generate is None
        assert args.scan is None
        assert args.format == "PNG"
        assert args.ec == "M"

    def test_parser_generate_flags(self):
        parser = build_cli_parser()
        args = parser.parse_args([
            "--generate", "https://example.com",
            "--output", "my_qr.svg",
            "--format", "SVG",
            "--fg", "#FF0000",
            "--bg", "#000000",
            "--ec", "H",
            "--size", "500",
        ])
        assert args.generate == "https://example.com"
        assert args.output == "my_qr.svg"
        assert args.format == "SVG"
        assert args.fg == "#FF0000"
        assert args.bg == "#000000"
        assert args.ec == "H"
        assert args.size == 500

    def test_cli_generate_png(self, tmp_path: Path):
        out_file = tmp_path / "cli_qr.png"
        parser = build_cli_parser()
        args = parser.parse_args([
            "--generate", "https://github.com",
            "--output", str(out_file),
            "--format", "PNG",
            "--ec", "Q",
        ])
        exit_code = handle_cli_generate(args)
        assert exit_code == 0
        assert out_file.exists()

    def test_cli_generate_invalid_payload(self, tmp_path: Path):
        out_file = tmp_path / "cli_qr.png"
        parser = build_cli_parser()
        # Invalid empty payload handled gracefully
        args = parser.parse_args([
            "--generate", "",
            "--output", str(out_file),
        ])
        exit_code = handle_cli_generate(args)
        # Should return 1 on error
        assert exit_code == 1

    def test_cli_scan_valid_file(self, tmp_path: Path):
        # Generate an image first
        from app.generator import QRGenerator
        qr_file = tmp_path / "test_scan.png"
        QRGenerator().export_file("https://antigravity.ai", qr_file)

        parser = build_cli_parser()
        args = parser.parse_args(["--scan", str(qr_file)])
        exit_code = handle_cli_scan(args)
        assert exit_code == 0

    def test_cli_scan_nonexistent_file(self):
        parser = build_cli_parser()
        args = parser.parse_args(["--scan", "non_existent_file_12345.png"])
        exit_code = handle_cli_scan(args)
        assert exit_code == 1
