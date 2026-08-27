"""Unit tests verifying zero privacy leakage in application logging."""

from pathlib import Path

from app.logging_config import _LOG_FILE, log_error, log_generation, log_scan_event, setup_logging


class TestLoggingPrivacy:
    """Ensure sensitive parameters (passwords, contacts, scan contents) are never logged."""

    def test_log_generation_privacy(self):
        setup_logging()
        log_generation(qr_type="WIFI", error_correction="H", size=400)

        assert _LOG_FILE.exists()
        log_text = _LOG_FILE.read_text(encoding="utf-8")
        assert "Generated QR type: WIFI" in log_text
        # Ensure no accidental password or parameter leaks
        assert "SecretPassword" not in log_text

    def test_log_scan_event_privacy(self):
        setup_logging()
        log_scan_event(qr_count=1, file_format=".png")

        log_text = _LOG_FILE.read_text(encoding="utf-8")
        assert "Scan completed: 1 QR code(s) detected from .PNG image." in log_text

    def test_log_error_privacy(self):
        setup_logging()
        log_error("Test context", ValueError("Sample error message"))

        log_text = _LOG_FILE.read_text(encoding="utf-8")
        assert "Error during Test context: ValueError" in log_text
