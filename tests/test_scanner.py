"""Unit tests for QR scanning, parsing, and OpenCV decoding."""

from pathlib import Path
from PIL import Image

from app.generator import QRGenerator
from app.payloads import (
    build_email_payload,
    build_location_payload,
    build_phone_payload,
    build_sms_payload,
    build_vcard_payload,
    build_wifi_payload,
)
from app.scanner import QRScanner, parse_payload


class TestScanner:
    """Test suite for payload parsing and QR image decoding."""

    def test_parse_wifi_payload(self):
        raw = "WIFI:T:WPA;S:MyNetwork;P:Secret123;H:false;;"
        res = parse_payload(raw)
        assert res.qr_type == "wifi"
        assert res.parsed_data["ssid"] == "MyNetwork"
        assert res.parsed_data["password"] == "Secret123"
        assert res.parsed_data["security"] == "WPA"
        assert res.parsed_data["hidden"] is False

    def test_parse_vcard_payload(self):
        raw = (
            "BEGIN:VCARD\r\n"
            "VERSION:3.0\r\n"
            "FN:Alice Wonderland\r\n"
            "ORG:Wonderland Inc\r\n"
            "TEL;TYPE=CELL,VOICE:+1234567890\r\n"
            "EMAIL;TYPE=INTERNET:alice@wonder.land\r\n"
            "END:VCARD"
        )
        res = parse_payload(raw)
        assert res.qr_type == "vcard"
        assert res.parsed_data["name"] == "Alice Wonderland"
        assert res.parsed_data["org"] == "Wonderland Inc"
        assert res.parsed_data["phone"] == "+1234567890"
        assert res.parsed_data["email"] == "alice@wonder.land"

    def test_parse_email_payload(self):
        raw = "mailto:support@service.io?subject=Help&body=Please+help"
        res = parse_payload(raw)
        assert res.qr_type == "email"
        assert res.parsed_data["email"] == "support@service.io"
        assert res.parsed_data["subject"] == "Help"

    def test_parse_phone_payload(self):
        raw = "tel:+18005550199"
        res = parse_payload(raw)
        assert res.qr_type == "phone"
        assert res.parsed_data["phone"] == "+18005550199"

    def test_parse_sms_payload(self):
        raw = "SMSTO:+18005550199:Hello there"
        res = parse_payload(raw)
        assert res.qr_type == "sms"
        assert res.parsed_data["phone"] == "+18005550199"
        assert res.parsed_data["message"] == "Hello there"

    def test_parse_location_payload(self):
        raw = "geo:37.774929,-122.419416"
        res = parse_payload(raw)
        assert res.qr_type == "location"
        assert res.parsed_data["latitude"] == 37.774929
        assert res.parsed_data["longitude"] == -122.419416
        assert "google.com/maps" in res.parsed_data["maps_url"]

    def test_parse_url_payload(self):
        raw = "https://github.com/trending"
        res = parse_payload(raw)
        assert res.qr_type == "url"
        assert res.parsed_data["domain"] == "github.com"

    def test_scan_generated_qr_image(self):
        gen = QRGenerator()
        scanner = QRScanner()

        test_payload = "https://antigravity.ai/test"
        img = gen.render_image(test_payload, target_size=400)

        results = scanner.scan_image(img)
        assert len(results) >= 1
        assert results[0].raw_text == test_payload
        assert results[0].qr_type == "url"

    def test_scan_wifi_qr_image(self):
        gen = QRGenerator()
        scanner = QRScanner()

        wifi_payload = build_wifi_payload("HomeOffice", "SuperSecretPass", "WPA")
        img = gen.render_image(wifi_payload, target_size=400)

        results = scanner.scan_image(img)
        assert len(results) >= 1
        assert results[0].qr_type == "wifi"
        assert results[0].parsed_data["ssid"] == "HomeOffice"
        assert results[0].parsed_data["password"] == "SuperSecretPass"

    def test_scan_empty_or_invalid_image(self):
        scanner = QRScanner()
        # Nonexistent path
        res = scanner.scan_image("non_existent_image_12345.png")
        assert res == []

        # Blank white image
        blank = Image.new("RGB", (200, 200), (255, 255, 255))
        res_blank = scanner.scan_image(blank)
        assert res_blank == []

    def test_parse_empty_payload(self):
        res = parse_payload("   ")
        assert res.raw_text == ""
        assert res.qr_type == "text"

