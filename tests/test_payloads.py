"""Unit tests for QR payload builders."""

import pytest

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


class TestPayloads:
    """Test suite verifying payload format compliance and escaping."""

    def test_build_text_payload(self):
        res = build_text_payload("   Sample text   ")
        assert res == "Sample text"

    def test_build_url_payload(self):
        res = build_url_payload("example.com/test")
        assert res == "https://example.com/test"

    def test_build_wifi_payload_wpa(self):
        res = build_wifi_payload(ssid="Cafe;WiFi", password="pass:word;123", security="WPA")
        # Ensure escaped characters
        assert "S:Cafe\\;WiFi;" in res
        assert "P:pass\\:word\\;123;" in res
        assert "T:WPA;" in res

    def test_build_wifi_payload_open(self):
        res = build_wifi_payload(ssid="Airport", security="nopass")
        assert res == "WIFI:T:nopass;S:Airport;H:false;;"

    def test_build_vcard_payload(self):
        res = build_vcard_payload(
            full_name="John Doe",
            org="Acme Inc",
            phone="+1234567890",
            email="john@acme.com",
            website="https://acme.com",
            address="100 Main St, Metropolis",
        )
        assert "BEGIN:VCARD" in res
        assert "VERSION:3.0" in res
        assert "FN:John Doe" in res
        assert "ORG:Acme Inc" in res
        assert "TEL;TYPE=CELL,VOICE:+1234567890" in res
        assert "EMAIL;TYPE=INTERNET:john@acme.com" in res
        assert "URL:https://acme.com" in res
        assert "END:VCARD" in res

    def test_build_email_payload_simple(self):
        res = build_email_payload("user@test.org")
        assert res == "mailto:user@test.org"

    def test_build_email_payload_with_params(self):
        res = build_email_payload("user@test.org", subject="Hello World", body="Test message")
        assert res.startswith("mailto:user@test.org?")
        assert "subject=Hello+World" in res or "subject=Hello%20World" in res

    def test_build_phone_payload(self):
        res = build_phone_payload("+1 (800) 555-0199")
        assert res == "tel:+18005550199"

    def test_build_sms_payload(self):
        res = build_sms_payload("+18005550199", "Meeting at 5pm")
        assert res == "SMSTO:+18005550199:Meeting at 5pm"

    def test_build_location_payload(self):
        res = build_location_payload(37.774929, -122.419416)
        assert res == "geo:37.774929,-122.419416"

    def test_build_payloads_error_raises(self):
        with pytest.raises(ValueError):
            build_text_payload("")

        with pytest.raises(ValueError):
            build_url_payload("invalid url scheme ftp://")

        with pytest.raises(ValueError):
            build_wifi_payload("", "pass")

        with pytest.raises(ValueError):
            build_vcard_payload("", "", "", "")

        with pytest.raises(ValueError):
            build_email_payload("invalid-email")

        with pytest.raises(ValueError):
            build_phone_payload("")

        with pytest.raises(ValueError):
            build_sms_payload("")

        with pytest.raises(ValueError):
            build_location_payload("invalid", "coords")

