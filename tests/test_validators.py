"""Unit tests for input validators."""

import pytest

from app.validators import (
    normalize_and_validate_url,
    validate_email,
    validate_location,
    validate_phone,
    validate_sms,
    validate_text,
    validate_vcard,
    validate_wifi,
)


class TestValidators:
    """Test suite for all payload validators."""

    def test_validate_text_valid(self):
        ok, msg = validate_text("Hello World")
        assert ok is True
        assert msg == ""

    def test_validate_text_empty(self):
        ok, msg = validate_text("   ")
        assert ok is False
        assert "cannot be empty" in msg

    def test_validate_url_with_scheme(self):
        ok, norm, msg = normalize_and_validate_url("https://example.com/path?a=1")
        assert ok is True
        assert norm == "https://example.com/path?a=1"
        assert msg == ""

    def test_validate_url_without_scheme_auto_prepends(self):
        ok, norm, msg = normalize_and_validate_url("github.com/org/repo")
        assert ok is True
        assert norm == "https://github.com/org/repo"
        assert msg == ""

    def test_validate_url_invalid(self):
        ok, norm, msg = normalize_and_validate_url("invalid url with spaces")
        assert ok is False

    def test_validate_email_valid(self):
        ok, msg = validate_email("developer@company.org")
        assert ok is True
        assert msg == ""

    def test_validate_email_invalid(self):
        ok, msg = validate_email("not-an-email")
        assert ok is False
        assert "valid email" in msg

    def test_validate_phone_valid(self):
        ok, msg = validate_phone("+1 (555) 234-5678")
        assert ok is True

    def test_validate_phone_too_short(self):
        ok, msg = validate_phone("1")
        assert ok is False

    def test_validate_wifi_wpa(self):
        ok, msg = validate_wifi(ssid="MyNetwork", password="SuperSecretPassword123", security="WPA")
        assert ok is True

    def test_validate_wifi_short_password(self):
        ok, msg = validate_wifi(ssid="MyNetwork", password="short", security="WPA2")
        assert ok is False
        assert "8 characters" in msg

    def test_validate_wifi_open(self):
        ok, msg = validate_wifi(ssid="FreeWiFi", password="", security="nopass")
        assert ok is True

    def test_validate_vcard_valid(self):
        ok, msg = validate_vcard(
            full_name="Alice Smith",
            org="Tech Corp",
            email="alice@tech.io",
            phone="+1234567890",
            website="https://alice.dev",
        )
        assert ok is True

    def test_validate_vcard_all_empty(self):
        ok, msg = validate_vcard(full_name="", org="", phone="", email="")
        assert ok is False
        assert "At least one" in msg

    def test_validate_location_valid(self):
        ok, lat, lon, msg = validate_location("37.7749", "-122.4194")
        assert ok is True
        assert pytest.approx(lat, 0.001) == 37.7749
        assert pytest.approx(lon, 0.001) == -122.4194

    def test_validate_location_out_of_bounds(self):
        ok, _, _, msg = validate_location("95.0", "10.0")
        assert ok is False
        assert "between -90.0 and +90.0" in msg

        ok2, _, _, msg2 = validate_location("10.0", "195.0")
        assert ok2 is False
        assert "between -180.0 and +180.0" in msg2

        ok3, _, _, _ = validate_location("not_a_num", "10.0")
        assert ok3 is False

        ok4, _, _, _ = validate_location("10.0", "not_a_num")
        assert ok4 is False

        ok5, _, _, _ = validate_location("", "")
        assert ok5 is False

    def test_validate_url_special_hosts(self):
        ok, norm, _ = normalize_and_validate_url("localhost:8080")
        assert ok is True
        assert norm == "https://localhost:8080"

        ok_ip, norm_ip, _ = normalize_and_validate_url("127.0.0.1:3000")
        assert ok_ip is True

        ok_bad_scheme, _, msg = normalize_and_validate_url("ftp://example.com")
        assert ok_bad_scheme is False
        assert "http:// or https://" in msg

        ok_empty, _, _ = normalize_and_validate_url("   ")
        assert ok_empty is False

    def test_validate_wifi_edge_cases(self):
        ok, msg = validate_wifi("", "password123", "WPA")
        assert ok is False
        assert "SSID" in msg

        ok_unsupported, msg_unsup = validate_wifi("SSID", "pass", "UNKNOWN_SEC")
        assert ok_unsupported is False
        assert "Unsupported security" in msg_unsup

        ok_wep_no_pass, msg_wep = validate_wifi("SSID", "", "WEP")
        assert ok_wep_no_pass is False
        assert "Password is required" in msg_wep

    def test_validate_phone_edge_cases(self):
        ok, _ = validate_phone("")
        assert ok is False

        ok_inv, _ = validate_phone("invalid_phone_letters")
        assert ok_inv is False

    def test_validate_email_edge_cases(self):
        ok, _ = validate_email("")
        assert ok is False

    def test_validate_vcard_edge_cases(self):
        ok, msg = validate_vcard(full_name="Bob", email="invalid-email")
        assert ok is False

        ok_ph, msg_ph = validate_vcard(full_name="Bob", phone="invalid_ph")
        assert ok_ph is False

        ok_web, msg_web = validate_vcard(full_name="Bob", website="invalid website with spaces")
        assert ok_web is False

